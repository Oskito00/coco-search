"""Items linked to a saved search."""

from __future__ import annotations

from flask import Blueprint, g, request

from app.api.errors import NotFound
from app.api.middleware import require_auth
from app.api.responses import paginated
from app.auth import SCOPE_SEARCHES_READ
from app.models import UserQuery, UserQueryItems

bp = Blueprint("items", __name__, url_prefix="/searches/<string:query_id>/items")

DEFAULT_PER_PAGE = 50
MAX_PER_PAGE = 200


@bp.get("")
@require_auth(SCOPE_SEARCHES_READ)
def list_items(query_id: str):
    _ensure_owned(query_id)
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(int(request.args.get("per_page", DEFAULT_PER_PAGE)), MAX_PER_PAGE)

    base = UserQueryItems.query.filter_by(query_id=query_id)
    total = base.count()
    rows = (
        base.order_by(UserQueryItems.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return paginated([_item_view(r) for r in rows], page, per_page, total)


def _ensure_owned(query_id: str) -> None:
    exists = UserQuery.query.filter_by(user_id=g.user.id, query_id=query_id).first()
    if exists is None:
        raise NotFound("Search not found", code="search_not_found")


def _item_view(query_item: UserQueryItems) -> dict:
    item = query_item.item
    return {
        "item_id": item.item_id,
        "ebay_id": item.ebay_id,
        "title": item.title,
        "price": item.price,
        "currency": item.currency,
        "url": item.url,
        "image_url": item.image_url,
        "condition": item.condition,
        "seller": item.seller,
        "marketplace": item.marketplace,
        "location_country": item.location_country,
        "end_time": item.end_time.isoformat() if item.end_time else None,
        "linked_at": query_item.created_at.isoformat() if query_item.created_at else None,
    }
