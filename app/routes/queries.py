from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.forms import DeleteForm, QueryForm
from app.models import (
    Item,
    ItemRelevanceFeedback,
    Keyword,
    KeywordItems,
    UserQuery,
    UserQueryItems,
    db,
)
from app.relevance import RelevanceFeedbackService
from app.repositories import ItemRepository
from app.utils.graph_helpers import get_price_data
from app.utils.price_helpers import remove_price_outliers
from app.utils.query_helpers import update_user_usage
from app.utils.text_helpers import item_matches_keywords

bp = Blueprint("queries", __name__, url_prefix="/queries")

VALID_FEEDBACK = {"relevant", "irrelevant"}


@dataclass(frozen=True)
class SearchFilters:
    """Route-facing filter snapshot for saved-search service calls."""

    min_price: Decimal | None
    max_price: Decimal | None
    item_location: str | None
    condition: str | None
    buying_options: str | None
    required_keywords: str
    excluded_keywords: str


@dataclass(frozen=True)
class SearchSchedule:
    """Route-facing schedule snapshot for saved-search service calls."""

    check_interval: int
    first_run: bool
    last_full_run: datetime | None
    next_full_run: datetime | None
    last_recent_run: datetime | None


@dataclass(frozen=True)
class SavedSearch:
    """Route-facing saved-search snapshot detached from SQLAlchemy."""

    id: Any
    user_id: int
    keyword_id: int
    keywords: str
    marketplace: str
    is_active: bool
    filters: SearchFilters
    schedule: SearchSchedule


def saved_search_from_model(user_query: UserQuery) -> SavedSearch:
    """Create a saved-search snapshot from the current database model."""

    keyword_text = user_query.keyword.keyword_text if user_query.keyword else ""
    return SavedSearch(
        id=user_query.query_id,
        user_id=user_query.user_id,
        keyword_id=user_query.keyword_id,
        keywords=keyword_text,
        marketplace=user_query.marketplace,
        is_active=user_query.is_active,
        filters=SearchFilters(
            min_price=user_query.min_price,
            max_price=user_query.max_price,
            item_location=_query_location_filter(user_query.item_location),
            condition=_optional_text(user_query.condition),
            buying_options=_optional_text(user_query.buying_options),
            required_keywords=_text_value(user_query.required_keywords),
            excluded_keywords=_text_value(user_query.excluded_keywords),
        ),
        schedule=SearchSchedule(
            check_interval=user_query.check_interval,
            first_run=bool(user_query.first_run),
            last_full_run=user_query.last_full_run,
            next_full_run=user_query.next_full_run,
            last_recent_run=user_query.last_recent_run,
        ),
    )


def to_ebay_search_params(saved_search: SavedSearch) -> dict[str, Any]:
    """Map a saved search into executor/search-client parameters."""

    filters = {
        "min_price": saved_search.filters.min_price,
        "max_price": saved_search.filters.max_price,
        "item_location": saved_search.filters.item_location,
        "condition": saved_search.filters.condition,
        "buying_options": saved_search.filters.buying_options,
    }
    return {
        "keywords": saved_search.keywords,
        "marketplace": saved_search.marketplace,
        "filters": {
            key: value for key, value in filters.items() if value not in (None, "")
        },
        "required_keywords": saved_search.filters.required_keywords,
        "excluded_keywords": saved_search.filters.excluded_keywords,
    }


@bp.route("/manage")
@login_required
def manage_queries():
    queries = (
        UserQuery.query.options(joinedload(UserQuery.keyword))
        .filter(UserQuery.user_id == current_user.id)
        .order_by(UserQuery.created_at.desc())
        .all()
    )
    total_queries = len(queries)
    active_queries = sum(1 for query in queries if query.is_active)
    return render_template(
        "queries/manage.html",
        queries=queries,
        delete_form=DeleteForm(),
        all_active=active_queries == total_queries,
    )


@bp.route("/edit_query/<string:query_id>", methods=["GET", "POST"])
def edit_query(query_id: str):
    auth_redirect = _require_authenticated_user()
    if auth_redirect:
        return auth_redirect

    user_query = _get_owned_query_or_403(query_id)
    form = QueryForm(obj=user_query)

    if request.method == "GET":
        form.keywords.data = user_query.keyword.keyword_text

    if not form.validate_on_submit():
        return render_template("queries/edit.html", form=form, query=user_query)

    try:
        _update_saved_search(user_query, form)
    except ValueError as exc:
        flash(str(exc), "danger")
        return render_template("queries/edit.html", form=form, query=user_query)
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error("Query update failed: %s", exc)
        flash(f"Error updating query: {exc}", "danger")
        return render_template("queries/edit.html", form=form, query=user_query)

    flash("Query updated successfully", "success")
    return redirect(url_for("queries.manage_queries"))


@bp.route("/delete_query/<string:query_id>", methods=["POST"])
def delete_query(query_id: str):
    auth_redirect = _require_authenticated_user()
    if auth_redirect:
        return auth_redirect

    user_query = _get_owned_query_or_403(query_id)

    try:
        _delete_saved_search(user_query)
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error("Query deletion failed: %s", exc)
        flash(f"Error deleting query: {exc}", "danger")
    else:
        flash("Query deleted successfully", "success")

    return redirect(url_for("queries.manage_queries"))


@bp.route("/create_query", methods=["GET", "POST"])
def create_query():
    auth_redirect = _require_authenticated_user()
    if auth_redirect:
        return auth_redirect

    form = QueryForm()
    if request.method == "GET":
        form.check_interval.data = 5

    if not form.validate_on_submit():
        return render_template("queries/create.html", form=form)

    try:
        _create_saved_search(form)
    except ValueError as exc:
        flash(str(exc), "danger")
        return render_template("queries/create.html", form=form)
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error("Query creation failed: %s", exc)
        _remove_usage_if_needed(form.check_interval.data)
        flash(f"Error creating query: {exc}", "danger")
        return render_template("queries/create.html", form=form)

    return redirect(url_for("queries.manage_queries"))


@bp.route("/queries/toggle_all", methods=["POST"])
@login_required
def toggle_all_queries():
    queries = UserQuery.query.filter_by(user_id=current_user.id).all()
    new_state = not any(query.is_active for query in queries)

    try:
        for query in queries:
            if query.is_active != new_state:
                _set_query_active_state(query, new_state)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")

    return redirect(url_for("queries.manage_queries"))


@bp.route("/<string:query_id>/toggle", methods=["POST"])
@login_required
def toggle_query(query_id: str):
    query = _get_owned_query_or_403(query_id)

    try:
        _set_query_active_state(query, not query.is_active)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")

    return redirect(url_for("queries.manage_queries"))


@bp.route("/<string:query_id>")
@login_required
def query_details(query_id: str):
    query = UserQuery.query.filter_by(
        user_id=current_user.id, query_id=query_id
    ).first_or_404()
    return render_template("queries/details.html", **_query_details_context(query))


@bp.route("/feedback/<string:query_id>/<int:item_id>", methods=["POST"])
@login_required
def submit_feedback(query_id: str, item_id: int):
    feedback = request.form.get("feedback")
    if feedback not in VALID_FEEDBACK:
        abort(400)

    user_query_item, allowed = RelevanceFeedbackService().record_item_feedback(
        current_user,
        query_id,
        item_id,
        feedback,
    )
    if not allowed:
        abort(403)

    if feedback == "irrelevant":
        prev_item_id = _previous_item_id(query_id, item_id)
        db.session.delete(user_query_item)
        db.session.commit()
        return _redirect_to_query_item(query_id, prev_item_id)

    db.session.commit()
    return _redirect_to_query_item(query_id, item_id)


def _require_authenticated_user():
    if current_user.is_authenticated:
        return None

    flash("You need to be logged in to perform this action.", "danger")
    return redirect(url_for("auth.login"))


def _get_owned_query_or_403(query_id: str) -> UserQuery:
    user_query = UserQuery.query.get_or_404(query_id)
    if user_query.user_id != current_user.id:
        abort(403)
    return user_query


def _create_saved_search(form: QueryForm) -> UserQuery:
    _add_usage_or_raise(form.check_interval.data)
    keyword = _get_or_create_keyword(form.keywords.data)

    if _find_duplicate_query(
        keyword.keyword_id, form.item_location.data, form.marketplace.data
    ):
        _remove_usage_if_needed(form.check_interval.data)
        raise ValueError("You already have a query with this keyword and marketplace")

    user_query = UserQuery()
    form.populate_obj(user_query)
    user_query.user_id = current_user.id
    user_query.keyword_id = keyword.keyword_id
    user_query.keyword = keyword
    user_query.created_at = datetime.now(timezone.utc)
    user_query.is_active = True

    db.session.add(user_query)
    db.session.flush()
    _load_historical_items(user_query)
    db.session.commit()
    return user_query


def _update_saved_search(user_query: UserQuery, form: QueryForm) -> None:
    if _identity_changed(user_query, form) and _find_duplicate_query(
        user_query.keyword_id,
        form.item_location.data,
        form.marketplace.data,
        exclude_query_id=user_query.query_id,
    ):
        raise ValueError("You already have a query with this keyword and marketplace")

    _replace_usage_interval(user_query.check_interval, form.check_interval.data)

    filters_changed = _filters_changed(user_query, form)
    form.populate_obj(user_query)
    user_query.updated_at = datetime.now(timezone.utc)

    if filters_changed:
        _sync_query_items_for_filters(user_query)

    db.session.commit()


def _delete_saved_search(user_query: UserQuery) -> None:
    old_interval = user_query.check_interval
    UserQueryItems.query.filter_by(query_id=user_query.query_id).delete()
    db.session.delete(user_query)
    _remove_usage_if_needed(old_interval)
    db.session.commit()


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


def _find_duplicate_query(
    keyword_id: int,
    item_location: str,
    marketplace: str,
    exclude_query_id: Any | None = None,
) -> UserQuery | None:
    query = UserQuery.query.filter(
        UserQuery.user_id == current_user.id,
        UserQuery.keyword_id == keyword_id,
        UserQuery.item_location == item_location,
        UserQuery.marketplace == marketplace,
    )
    if exclude_query_id is not None:
        query = query.filter(UserQuery.query_id != exclude_query_id)
    return query.first()


def _identity_changed(user_query: UserQuery, form: QueryForm) -> bool:
    return (
        user_query.item_location != form.item_location.data
        or user_query.marketplace != form.marketplace.data
    )


def _filters_changed(user_query: UserQuery, form: QueryForm) -> bool:
    return (
        _text_value(user_query.required_keywords)
        != _text_value(form.required_keywords.data)
        or _text_value(user_query.excluded_keywords)
        != _text_value(form.excluded_keywords.data)
        or user_query.item_location != form.item_location.data
        or user_query.marketplace != form.marketplace.data
    )


def _load_historical_items(user_query: UserQuery) -> int:
    saved_search = saved_search_from_model(user_query)
    repository = ItemRepository()
    linked_count = 0

    for item in _historical_items_for_search(saved_search):
        if _feedback_blocks_item(
            user_query.user_id, user_query.keyword_id, item.item_id
        ):
            continue

        if repository.link_query(user_query.query_id, item.item_id):
            linked_count += 1

    return linked_count


def _sync_query_items_for_filters(user_query: UserQuery) -> None:
    saved_search = saved_search_from_model(user_query)
    existing_item_ids = select(UserQueryItems.item_id).where(
        UserQueryItems.query_id == user_query.query_id
    )

    for query_item in UserQueryItems.query.filter_by(
        query_id=user_query.query_id
    ).all():
        if not _item_matches_saved_search(query_item.item, saved_search):
            db.session.delete(query_item)

    repository = ItemRepository()
    for item in _historical_items_for_search(
        saved_search, excluded_item_ids=existing_item_ids
    ):
        if _feedback_blocks_item(
            user_query.user_id, user_query.keyword_id, item.item_id
        ):
            continue
        repository.link_query(user_query.query_id, item.item_id)


def _historical_items_for_search(
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

    if saved_search.filters.item_location is not None:
        query = query.filter(
            Item.location_country == saved_search.filters.item_location
        )

    if excluded_item_ids is not None:
        query = query.filter(~Item.item_id.in_(excluded_item_ids))

    return [
        item for item in query.all() if _item_matches_saved_search(item, saved_search)
    ]


def _item_matches_saved_search(item: Item, saved_search: SavedSearch) -> bool:
    location = saved_search.filters.item_location
    if location is not None and item.location_country != location:
        return False

    if item.marketplace != saved_search.marketplace:
        return False

    return item_matches_keywords(
        item,
        saved_search.filters.required_keywords,
        saved_search.filters.excluded_keywords,
    )


def _feedback_blocks_item(user_id: int, keyword_id: int, item_id: int) -> bool:
    feedback = ItemRelevanceFeedback.query.filter_by(
        user_id=user_id,
        item_id=item_id,
        keyword_id=keyword_id,
    ).first()
    return bool(feedback and feedback.is_relevant is False)


def _query_details_context(query: UserQuery) -> dict[str, Any]:
    all_items = (
        UserQueryItems.query.filter_by(query_id=query.query_id)
        .order_by(UserQueryItems.created_at.desc())
        .all()
    )
    filtered_items, auction_items, _outliers = _split_price_filtered_items(all_items)
    visible_items = filtered_items[:100] + auction_items[:100]
    price_data, average_price_last_30_days, most_frequent_currency = get_price_data(
        filtered_items
    )

    return {
        "query": query,
        "items": visible_items,
        "auction_items": auction_items,
        "stats": {"total_items": len(filtered_items + auction_items)},
        "price_data": price_data,
        "average_price_last_30_days": average_price_last_30_days,
        "most_frequent_currency": most_frequent_currency,
    }


def _split_price_filtered_items(
    items: list[UserQueryItems],
) -> tuple[list[UserQueryItems], list[UserQueryItems], list[UserQueryItems]]:
    result = remove_price_outliers(items)
    if not result:
        return [], [], []

    filtered_items = result[0]
    auction_items = result[1] if len(result) > 1 else []
    outliers = result[2] if len(result) > 2 else []
    return filtered_items, auction_items, outliers


def _previous_item_id(query_id: str, item_id: int) -> int | None:
    ordered_items = (
        UserQueryItems.query.filter_by(query_id=query_id)
        .order_by(UserQueryItems.created_at.asc())
        .all()
    )
    item_ids = [item.item_id for item in ordered_items]

    try:
        current_idx = item_ids.index(item_id)
    except ValueError:
        return None

    return item_ids[current_idx - 1] if current_idx > 0 else None


def _redirect_to_query_item(query_id: str, item_id: int | None):
    details_url = url_for("queries.query_details", query_id=query_id)
    if item_id is None:
        return redirect(details_url)
    return redirect(f"{details_url}#item-{item_id}")


def _set_query_active_state(query: UserQuery, is_active: bool) -> None:
    operation = "add" if is_active else "remove"
    update_user_usage(current_user, query.check_interval, operation)
    query.is_active = is_active


def _replace_usage_interval(old_interval: int, new_interval: int) -> None:
    if old_interval == new_interval:
        return

    _remove_usage_if_needed(old_interval)
    try:
        _add_usage_or_raise(new_interval)
    except ValueError:
        _add_usage_or_raise(old_interval)
        raise


def _add_usage_or_raise(check_interval: int) -> None:
    update_user_usage(current_user, check_interval, "add")


def _remove_usage_if_needed(check_interval: int | None) -> None:
    if check_interval is not None:
        update_user_usage(current_user, check_interval, "remove")


def _query_location_filter(item_location: str | None) -> str | None:
    return None if item_location in (None, "", "any") else item_location


def _optional_text(value: str | None) -> str | None:
    return value or None


def _text_value(value: str | None) -> str:
    return value or ""
