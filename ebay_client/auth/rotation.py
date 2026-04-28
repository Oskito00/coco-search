"""Round-robin credential rotation helpers."""

from __future__ import annotations

from collections.abc import MutableSequence
from typing import Any

Credential = dict[str, Any]


class CredentialRotator:
    """Track round-robin credential selection and expose the active index."""

    def __init__(
        self, credentials: MutableSequence[Credential], start_index: int = 0
    ) -> None:
        """Create a rotator for a mutable credential sequence."""
        if not credentials:
            raise ValueError("At least one eBay credential is required")
        self._credentials = credentials
        self.index = start_index % len(credentials)

    @property
    def index(self) -> int:
        """Return the index that will be used by the next rotation."""
        return self._index

    @index.setter
    def index(self, value: int) -> None:
        self._index = value % len(self._credentials)

    def next(self) -> Credential:
        """Return the current credential and advance the index."""
        credential = self._credentials[self.index]
        self.index = self.index + 1
        return credential
