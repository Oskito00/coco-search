"""Authentication endpoints: register, login, email confirm, password reset, tokens."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, g, render_template

from app.api.errors import BadRequest, Conflict, NotFound, Unauthorized
from app.api.middleware import require_auth
from app.api.responses import created, ok
from app.api.schemas import Field, get_json, validate
from app.auth import (
    ALL_SCOPES,
    DEFAULT_SCOPES,
    confirm_email_token,
    generate_email_token,
    issue_token,
    revoke_token,
)
from app.extensions import db
from app.models import ApiToken, User
from app.utils.email import send_email, send_password_reset_email

bp = Blueprint("auth", __name__, url_prefix="/auth")


_REGISTER_SCHEMA = {
    "email": Field(str, required=True),
    "password": Field(str, required=True, min=8),
}

_LOGIN_SCHEMA = {
    "email": Field(str, required=True),
    "password": Field(str, required=True),
    "token_name": Field(str, default="login"),
}

_FORGOT_SCHEMA = {"email": Field(str, required=True)}

_RESET_SCHEMA = {
    "token": Field(str, required=True),
    "password": Field(str, required=True, min=8),
}

_RESEND_SCHEMA = {"email": Field(str, required=True)}

_TOKEN_CREATE_SCHEMA = {
    "name": Field(str, required=True, min=1),
    "scopes": Field(list, default=None),
}


@bp.post("/register")
def register():
    payload = validate(get_json(), _REGISTER_SCHEMA)
    email = payload["email"].lower().strip()

    if User.query.filter_by(email=email).first():
        raise Conflict("Email already registered", code="email_taken")

    user = User(email=email)
    user.set_password(payload["password"])
    db.session.add(user)
    db.session.commit()

    _send_verification_email(user)
    return created({"id": user.id, "email": user.email, "email_verified": False})


@bp.post("/login")
def login():
    payload = validate(get_json(), _LOGIN_SCHEMA)
    user = _find_user_or_unauthorized(payload["email"])
    if not user.check_password(payload["password"]):
        raise Unauthorized("Invalid credentials", code="invalid_credentials")
    if not user.email_verified:
        raise Unauthorized("Email not verified", code="email_not_verified")

    issued = issue_token(user, name=payload["token_name"], scopes=DEFAULT_SCOPES)
    user.last_login = datetime.utcnow()
    db.session.commit()
    return created(_token_view(issued.record, raw=issued.raw))


@bp.post("/confirm")
def confirm_email():
    payload = validate(get_json(), {"token": Field(str, required=True)})
    email = confirm_email_token(payload["token"])
    if not email:
        raise BadRequest("Invalid or expired token", code="invalid_token")

    user = User.query.filter_by(email=email).first()
    if user is None:
        raise NotFound("User not found", code="user_not_found")
    if not user.email_verified:
        user.email_verified = True
        user.email_verified_on = datetime.utcnow()
        db.session.commit()
    return ok({"id": user.id, "email": user.email, "email_verified": True})


@bp.post("/resend-verification")
def resend_verification():
    payload = validate(get_json(), _RESEND_SCHEMA)
    user = User.query.filter_by(email=payload["email"].lower().strip()).first()
    if user and not user.email_verified:
        _send_verification_email(user)
    return ok({"sent": True})


@bp.post("/forgot-password")
def forgot_password():
    payload = validate(get_json(), _FORGOT_SCHEMA)
    user = User.query.filter_by(email=payload["email"].lower().strip()).first()
    if user is not None:
        _send_password_reset_email(user)
    return ok({"sent": True})


@bp.post("/reset-password")
def reset_password():
    payload = validate(get_json(), _RESET_SCHEMA)
    email = confirm_email_token(payload["token"])
    if not email:
        raise BadRequest("Invalid or expired token", code="invalid_token")

    user = User.query.filter_by(email=email).first()
    if user is None:
        raise NotFound("User not found", code="user_not_found")

    user.set_password(payload["password"])
    db.session.commit()
    return ok({"reset": True})


@bp.get("/tokens")
@require_auth()
def list_tokens():
    records = (
        ApiToken.query.filter_by(user_id=g.user.id)
        .order_by(ApiToken.created_at.desc())
        .all()
    )
    return ok([_token_view(r) for r in records])


@bp.post("/tokens")
@require_auth()
def create_token():
    payload = validate(get_json(), _TOKEN_CREATE_SCHEMA)
    scopes = _resolve_requested_scopes(payload.get("scopes"))
    issued = issue_token(g.user, name=payload["name"], scopes=scopes)
    db.session.commit()
    return created(_token_view(issued.record, raw=issued.raw))


@bp.delete("/tokens/<int:token_id>")
@require_auth()
def revoke_token_route(token_id: int):
    record = ApiToken.query.filter_by(id=token_id, user_id=g.user.id).first()
    if record is None:
        raise NotFound("Token not found", code="token_not_found")
    revoke_token(record)
    db.session.commit()
    return ok({"revoked": True})


def _find_user_or_unauthorized(email: str) -> User:
    user = User.query.filter_by(email=email.lower().strip()).first()
    if user is None:
        raise Unauthorized("Invalid credentials", code="invalid_credentials")
    return user


def _resolve_requested_scopes(requested: list | None) -> list[str]:
    if requested is None:
        return list(DEFAULT_SCOPES)
    invalid = [s for s in requested if s not in ALL_SCOPES]
    if invalid:
        raise BadRequest(f"Unknown scopes: {invalid}", code="invalid_scopes")
    return list(requested)


def _token_view(record: ApiToken, raw: str | None = None) -> dict:
    view = {
        "id": record.id,
        "name": record.name,
        "prefix": record.token_prefix,
        "scopes": record.scopes,
        "created_at": _iso(record.created_at),
        "last_used_at": _iso(record.last_used_at),
        "expires_at": _iso(record.expires_at),
        "revoked_at": _iso(record.revoked_at),
    }
    if raw is not None:
        view["token"] = raw
    return view


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _send_verification_email(user: User) -> None:
    token = generate_email_token(user.email)
    confirm_url = _client_url("/auth/confirm", token)
    html = render_template("email/verification.html", confirm_url=confirm_url)
    send_email(user.email, "Please confirm your email", html)


def _send_password_reset_email(user: User) -> None:
    token = generate_email_token(user.email)
    reset_url = _client_url("/auth/reset-password", token)
    html = render_template("email/password_reset.html", reset_url=reset_url)
    send_password_reset_email(user.email, html)


def _client_url(path: str, token: str) -> str:
    base = current_app.config.get("PUBLIC_APP_URL", "").rstrip("/")
    return f"{base}{path}?token={token}"
