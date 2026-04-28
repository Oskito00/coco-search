from datetime import datetime, timedelta, timezone


class TokenExpiryPolicy:
    def __init__(self, refresh_margin_seconds=60, clock=None):
        self.refresh_margin = timedelta(seconds=refresh_margin_seconds)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def needs_refresh(self, credential):
        if not credential.token:
            return True

        if not credential.token_expiry:
            return False

        return self.clock() > (credential.token_expiry - self.refresh_margin)
