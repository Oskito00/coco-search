"""Saved-search CRUD + activation + feedback."""

from __future__ import annotations

from flask import Blueprint, g

from app.api.errors import BadRequest, Conflict, Forbidden, NotFound
from app.api.middleware import require_auth
from app.api.responses import created, no_content, ok
from app.api.schemas import Field, get_json, validate
from app.auth import SCOPE_SEARCHES_READ, SCOPE_SEARCHES_WRITE
from app.extensions import db
from app.models import UserQuery, UserQueryItems
from app.relevance import RelevanceFeedbackService
from app.searches import saved_search_service as service
from app.searches.saved_search_service import SavedSearchParams

bp = Blueprint("searches", __name__, url_prefix="/searches")

_NUMERIC = (int, float)

_CREATE_SCHEMA = {
    "keywords": Field(str, required=True),
    "check_interval": Field(int, required=True, min=5, max=120),
    "marketplace": Field(str, default="EBAY_GB"),
    "item_location": Field(str, default="any"),
    "min_price": Field(_NUMERIC, default=None),
    "max_price": Field(_NUMERIC, default=None),
    "condition": Field(str, default=None, choices=[None, "", "NEW", "USED"]),
    "required_keywords": Field(str, default=None),
    "excluded_keywords": Field(str, default=None),
    "buying_options": Field(str, default=None),
}

_TOGGLE_SCHEMA = {"is_active": Field(bool, required=True)}

_FEEDBACK_SCHEMA = {
    "feedback": Field(str, required=True, choices=["relevant", "irrelevant"]),
}


@bp.get("")
@require_auth(SCOPE_SEARCHES_READ)
def list_searches():
    rows = service.list_searches(g.user.id)
    return ok([_search_view(row) for row in rows])


@bp.post("")
@require_auth(SCOPE_SEARCHES_WRITE)
def create_search():
    params = SavedSearchParams.from_dict(validate(get_json(), _CREATE_SCHEMA))
    try:
        user_query = service.create_search(g.user, params)
    except ValueError as exc:
        raise Conflict(str(exc), code="duplicate_search")
    return created(_search_view(user_query))


@bp.get("/<string:query_id>")
@require_auth(SCOPE_SEARCHES_READ)
def get_search(query_id: str):
    user_query = _owned_search(query_id)
    return ok(_search_view(user_query, include_items=True))


@bp.patch("/<string:query_id>")
@require_auth(SCOPE_SEARCHES_WRITE)
def update_search(query_id: str):
    user_query = _owned_search(query_id)
    params = SavedSearchParams.from_dict(validate(get_json(), _CREATE_SCHEMA))
    try:
        service.update_search(user_query, params)
    except ValueError as exc:
        raise Conflict(str(exc), code="duplicate_search")
    return ok(_search_view(user_query))


@bp.delete("/<string:query_id>")
@require_auth(SCOPE_SEARCHES_WRITE)
def delete_search(query_id: str):
    user_query = _owned_search(query_id)
    service.delete_search(user_query)
    return no_content()


@bp.post("/<string:query_id>/toggle")
@require_auth(SCOPE_SEARCHES_WRITE)
def toggle_search(query_id: str):
    user_query = _owned_search(query_id)
    payload = validate(get_json(), _TOGGLE_SCHEMA)
    try:
        service.set_active(user_query, payload["is_active"])
    except ValueError as exc:
        raise BadRequest(str(exc), code="quota_exceeded")
    return ok(_search_view(user_query))


@bp.post("/toggle-all")
@require_auth(SCOPE_SEARCHES_WRITE)
def toggle_all():
    payload = validate(get_json(), _TOGGLE_SCHEMA)
    changed = service.set_active_for_all(g.user, payload["is_active"])
    return ok({"changed": changed, "is_active": payload["is_active"]})


@bp.post("/<string:query_id>/items/<int:item_id>/feedback")
@require_auth(SCOPE_SEARCHES_WRITE)
def submit_feedback(query_id: str, item_id: int):
    payload = validate(get_json(), _FEEDBACK_SCHEMA)
    user_query_item, allowed = RelevanceFeedbackService().record_item_feedback(
        g.user, query_id, item_id, payload["feedback"]
    )
    if not allowed:
        raise Forbidden("Cannot submit feedback for this item", code="feedback_forbidden")

    if payload["feedback"] == "irrelevant":
        db.session.delete(user_query_item)
    db.session.commit()
    return ok({"feedback": payload["feedback"]})


def _owned_search(query_id: str) -> UserQuery:
    user_query = service.get_search(g.user.id, query_id)
    if user_query is None:
        raise NotFound("Search not found", code="search_not_found")
    return user_query


def _search_view(query: UserQuery, include_items: bool = False) -> dict:
    view = {
        "query_id": str(query.query_id),
        "keywords": query.keyword.keyword_text if query.keyword else None,
        "is_active": query.is_active,
        "check_interval": query.check_interval,
        "marketplace": query.marketplace,
        "item_location": query.item_location,
        "min_price": _decimal(query.min_price),
        "max_price": _decimal(query.max_price),
        "condition": query.condition,
        "required_keywords": query.required_keywords,
        "excluded_keywords": query.excluded_keywords,
        "buying_options": query.buying_options,
        "first_run": query.first_run,
        "last_full_run": _iso(query.last_full_run),
        "next_full_run": _iso(query.next_full_run),
        "last_recent_run": _iso(query.last_recent_run),
        "average_relevance_score": query.average_relevance_score,
        "created_at": _iso(query.created_at),
    }
    if include_items:
        view["items_count"] = UserQueryItems.query.filter_by(query_id=query.query_id).count()
    return view


def _iso(value):
    return value.isoformat() if value else None


def _decimal(value):
    return float(value) if value is not None else None
