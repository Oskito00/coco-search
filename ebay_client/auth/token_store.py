"""Token persistence helpers for eBay OAuth credentials."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ebay_client.auth.datetime_utils import parse_datetime, serialize_datetime

TokenRecord = dict[str, Any]


class EbayTokenStore:
    """Persist eBay OAuth tokens as JSON keyed by client id."""

    def __init__(self, path: str | Path) -> None:
        """Create a token store that reads and writes the given JSON file."""
        self.path = Path(path)

    def load(self) -> dict[str, TokenRecord]:
        """Load token records from disk, returning an empty mapping if absent."""
        if not self.path.exists():
            return {}

        with self.path.open("r", encoding="utf-8") as token_file:
            raw_records = json.load(token_file)

        if not isinstance(raw_records, Mapping):
            raise ValueError("Token store must contain an object keyed by client id")

        return {
            str(client_id): normalize_token_record(record)
            for client_id, record in raw_records.items()
        }

    def save(self, records: Mapping[str, Mapping[str, Any]]) -> None:
        """Persist token records to disk with datetime values serialized."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            str(client_id): serialize_token_record(record)
            for client_id, record in records.items()
        }

        with self.path.open("w", encoding="utf-8") as token_file:
            json.dump(serializable, token_file, indent=2, sort_keys=True)

    def update_credential(self, credential: TokenRecord) -> None:
        """Merge a credential's current token fields into the persisted store."""
        client_id = credential.get("client_id")
        if not client_id:
            raise ValueError("Credential requires client_id before it can be stored")

        records = self.load()
        records[str(client_id)] = {
            "token": credential.get("token"),
            "token_expiry": credential.get("token_expiry"),
        }
        self.save(records)

    def apply_to_credentials(self, credentials: list[TokenRecord]) -> None:
        """Apply persisted token fields to matching credentials in place."""
        records = self.load()
        for credential in credentials:
            record = records.get(str(credential.get("client_id")))
            if record:
                credential["token"] = record.get("token")
                credential["token_expiry"] = record.get("token_expiry")


def normalize_token_record(raw_record: object) -> TokenRecord:
    """Normalize one token record loaded from JSON."""
    if not isinstance(raw_record, Mapping):
        raise ValueError("Token records must be objects")

    return {
        "token": raw_record.get("token"),
        "token_expiry": parse_datetime(raw_record.get("token_expiry")),
    }


def serialize_token_record(record: Mapping[str, Any]) -> TokenRecord:
    """Convert one token record into a JSON-serializable mapping."""
    return {
        "token": record.get("token"),
        "token_expiry": serialize_datetime(record.get("token_expiry")),
    }


def load_tokens(path: str | Path) -> dict[str, TokenRecord]:
    """Load tokens from a JSON file."""
    return EbayTokenStore(path).load()


def save_tokens(path: str | Path, records: Mapping[str, Mapping[str, Any]]) -> None:
    """Save tokens to a JSON file."""
    EbayTokenStore(path).save(records)
