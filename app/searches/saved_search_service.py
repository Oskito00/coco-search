"""User-facing saved-search operations: CRUD, toggle, with quota + duplicate guards.

Pure-data inputs (no Flask form objects) so it can be called from API routes,
background jobs, or future agent code without coupling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.extensions import db
from app.models import (
    Item,
    ItemRelevanceFeedback,
    Keyword,
    KeywordItems,
    User,
    UserQuery,
    UserQueryItems,
)
from app.repositories import ItemRepository
from app.searches import SavedSearch, saved_search_from_model
from app.utils.query_helpers import update_user_usage
from app.utils.text_helpers import item_matches_keywords


@dataclass(frozen=True)
class SavedSearchParams:
    keywords: str
    check_interval: int
    marketplace: str = "EBAY_GB"
    item_location: str = "any"
    min_price: float | None = None
    max_price: float | None = None
    condition: str | None = None
    required_keywords: str | None = None
    excluded_keywords: str | None = None
    buying_options: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "SavedSearchParams":
        return cls(
            keywords=data["keywords"],
            check_interval=int(data["check_interval"]),
            marketplace=data.get("marketplace") or "EBAY_GB",
            item_location=data.get("item_location") or "any",
            min_price=data.get("min_price"),
            max_price=data.get("max_price"),
            condition=data.get("condition") or None,
            required_keywords=data.get("required_keywords") or None,
            excluded_keywords=data.get("excluded_keywords") or None,
            buying_options=data.get("buying_options") or None,
        )


def list_searches(user_id: int) -> list[UserQuery]:
    return (
        UserQuery.query.filter_by(user_id=user_id)
        .order_by(UserQuery.created_at.desc())
        .all()
    )


def get_search(user_id: int, query_id: str) -> UserQuery | None:
    return UserQuery.query.filter_by(user_id=user_id, query_id=query_id).first()


def create_search(user: User, params: SavedSearchParams) -> UserQuery:
    update_user_usage(user, params.check_interval, "add")
    keyword = _get_or_create_keyword(params.keywords)

    if _find_duplicate(user.id, keyword.keyword_id, params):
        update_user_usage(user, params.check_interval, "remove")
        raise ValueError("You already have a query with this keyword and marketplace")

    user_query = _build_user_query(user, keyword, params)
    db.session.add(user_query)
    db.session.flush()
    _load_historical_items(user_query)
    db.session.commit()
    return user_query


def update_search(user_query: UserQuery, params: SavedSearchParams) -> UserQuery:
    if _identity_changed(user_query, params) and _find_duplicate(
        user_query.user_id,
        user_query.keyword_id,
        params,
        exclude_query_id=user_query.query_id,
    ):
        raise ValueError("You already have a query with this keyword and marketplace")

    _replace_usage_interval(user_query.user, user_query.check_interval, params.check_interval)
    filters_changed = _filters_changed(user_query, params)
    _apply_params(user_query, params)

    if filters_changed:
        _sync_query_items(user_query)

    db.session.commit()
    return user_query


def delete_search(user_query: UserQuery) -> None:
    user = user_query.user
    interval = user_query.check_interval
    UserQueryItems.query.filter_by(query_id=user_query.query_id).delete()
    db.session.delete(user_query)
    update_user_usage(user, interval, "remove")
    db.session.commit()


def set_active(user_query: UserQuery, is_active: bool) -> None:
    if user_query.is_active == is_active:
        return
    operation = "add" if is_active else "remove"
    update_user_usage(user_query.user, user_query.check_interval, operation)
    user_query.is_active = is_active
    db.session.commit()


def set_active_for_all(user: User, is_active: bool) -> int:
    changed = 0
    for query in UserQuery.query.filter_by(user_id=user.id).all():
        if query.is_active != is_active:
            update_user_usage(user, query.check_interval, "add" if is_active else "remove")
            query.is_active = is_active
            changed += 1
    db.session.commit()
    return changed


def _build_user_query(user: User, keyword: Keyword, params: SavedSearchParams) -> UserQuery:
    user_query = UserQuery(
        user_id=user.id,
        keyword_id=keyword.keyword_id,
        keyword=keyword,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    _apply_params(user_query, params)
    return user_query


def _apply_params(user_query: UserQuery, params: SavedSearchParams) -> None:
    user_query.check_interval = params.check_interval
    user_query.marketplace = params.marketplace
    user_query.item_location = params.item_location
    user_query.min_price = params.min_price
    user_query.max_price = params.max_price
    user_query.condition = params.condition
    user_query.required_keywords = params.required_keywords
    user_query.excluded_keywords = params.excluded_keywords
    user_query.buying_options = params.buying_options


def _get_or_create_keyword(keyword_text: str) -> Keyword:
    cleaned = keyword_text.strip()
    keyword = Keyword.query.filter(
        db.func.lower(Keyword.keyword_text) == db.func.lower(cleaned)
    ).first()
    if keyword:
        return keyword

    keyword = Keyword(keyword_text=cleaned)
    db.session.add(keyword)
    db.session.flush()
    return keyword


def _find_duplicate(
    user_id: int,
    keyword_id: int,
    params: SavedSearchParams,
    exclude_query_id: Any | None = None,
) -> UserQuery | None:
    query = UserQuery.query.filter(
        UserQuery.user_id == user_id,
        UserQuery.keyword_id == keyword_id,
        UserQuery.item_location == params.item_location,
        UserQuery.marketplace == params.marketplace,
    )
    if exclude_query_id is not None:
        query = query.filter(UserQuery.query_id != exclude_query_id)
    return query.first()


def _identity_changed(user_query: UserQuery, params: SavedSearchParams) -> bool:
    return (
        user_query.item_location != params.item_location
        or user_query.marketplace != params.marketplace
    )


def _filters_changed(user_query: UserQuery, params: SavedSearchParams) -> bool:
    return (
        _text(user_query.required_keywords) != _text(params.required_keywords)
        or _text(user_query.excluded_keywords) != _text(params.excluded_keywords)
        or user_query.item_location != params.item_location
        or user_query.marketplace != params.marketplace
    )


def _replace_usage_interval(user: User, old: int, new: int) -> None:
    if old == new:
        return
    update_user_usage(user, old, "remove")
    try:
        update_user_usage(user, new, "add")
    except ValueError:
        update_user_usage(user, old, "add")
        raise


def _load_historical_items(user_query: UserQuery) -> int:
    saved_search = saved_search_from_model(user_query)
    repository = ItemRepository()
    linked = 0
    for item in _historical_items(saved_search):
        if _feedback_blocks(user_query.user_id, user_query.keyword_id, item.item_id):
            continue
        if repository.link_query(user_query.query_id, item.item_id):
            linked += 1
    return linked


def _sync_query_items(user_query: UserQuery) -> None:
    saved_search = saved_search_from_model(user_query)
    existing_ids = select(UserQueryItems.item_id).where(
        UserQueryItems.query_id == user_query.query_id
    )

    for query_item in UserQueryItems.query.filter_by(query_id=user_query.query_id).all():
        if not _matches(query_item.item, saved_search):
            db.session.delete(query_item)

    repository = ItemRepository()
    for item in _historical_items(saved_search, excluded_item_ids=existing_ids):
        if _feedback_blocks(user_query.user_id, user_query.keyword_id, item.item_id):
            continue
        repository.link_query(user_query.query_id, item.item_id)


def _historical_items(
    saved_search: SavedSearch,
    excluded_item_ids: Any | None = None,
) -> list[Item]:
    query = (
        db.session.query(Item)
        .join(KeywordItems, Item.item_id == KeywordItems.item_id)
        .filter(
            KeywordItems.keyword_id == saved_search.keyword_id,
            Item.marketplace == saved_search.marketplace,
        )
    )
    location = _location_filter(saved_search)
    if location is not None:
        query = query.filter(Item.location_country == location)
    if excluded_item_ids is not None:
        query = query.filter(~Item.item_id.in_(excluded_item_ids))
    return [item for item in query.all() if _matches(item, saved_search)]


def _matches(item: Item, saved_search: SavedSearch) -> bool:
    location = _location_filter(saved_search)
    if location is not None and item.location_country != location:
        return False
    if item.marketplace != saved_search.marketplace:
        return False
    return item_matches_keywords(
        item,
        _text(saved_search.filters.required_keywords),
        _text(saved_search.filters.excluded_keywords),
    )


def _location_filter(saved_search: SavedSearch) -> str | None:
    location = saved_search.filters.item_location
    return None if location in (None, "", "any") else location


def _feedback_blocks(user_id: int, keyword_id: int, item_id: int) -> bool:
    feedback = ItemRelevanceFeedback.query.filter_by(
        user_id=user_id,
        item_id=item_id,
        keyword_id=keyword_id,
    ).first()
    return bool(feedback and feedback.is_relevant is False)


def _text(value: str | None) -> str:
    return value or ""
