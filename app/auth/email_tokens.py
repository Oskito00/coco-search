"""Time-limited tokens for email confirmation and password reset."""

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

EMAIL_CONFIRM_MAX_AGE = 3600


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_email_token(email: str) -> str:
    salt = current_app.config["SECURITY_PASSWORD_SALT"]
    return _serializer().dumps(email, salt=salt)


def confirm_email_token(token: str, max_age: int = EMAIL_CONFIRM_MAX_AGE) -> str | None:
    salt = current_app.config["SECURITY_PASSWORD_SALT"]
    try:
        return _serializer().loads(token, salt=salt, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
