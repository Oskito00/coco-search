from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EbayCredential:
    client_id: str
    client_secret: str
    token: Optional[str] = None
    token_expiry: Optional[datetime] = None

    @classmethod
    def from_mapping(cls, credential):
        return cls(
            client_id=credential["client_id"],
            client_secret=credential["client_secret"],
            token=credential.get("token"),
            token_expiry=credential.get("token_expiry"),
        )

    def update_mapping(self, credential):
        credential.update(
            {
                "token": self.token,
                "token_expiry": self.token_expiry,
            }
        )
