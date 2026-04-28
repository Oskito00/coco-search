from datetime import datetime
from typing import Any, Optional

from app.extensions import db
from app.models import Item, ItemRelevanceFeedback, KeywordItems, UserQueryItems
from app.repositories._models import model_columns, update_model


class GlobalItemRepository:
    """Persistence operations for globally de-duplicated eBay items."""

    def __init__(self, session: Optional[Any] = None):
        self.session = session or db.session
        self.item_columns = model_columns(Item)

    def get(self, item_id: int) -> Optional[Item]:
        """Return one item by internal id."""
        return self.session.get(Item, item_id)

    def get_by_ebay_id(self, ebay_id: str) -> Optional[Item]:
        """Return one item by eBay id."""
        return Item.query.filter_by(ebay_id=ebay_id).first()

    def create(self, item_data: dict[str, Any]) -> Item:
        """Create an item from eBay payload data."""
        valid_data = {
            key: value for key, value in item_data.items() if key in self.item_columns
        }
        item = Item(**valid_data)
        location = item_data.get("location") or {}
        item.location_country = location.get("country")
        item.postal_code = location.get("postal_code")
        self.session.add(item)
        self.session.flush()
        return item

    def update(
        self, item: Item, item_data: dict[str, Any], updated_at: datetime
    ) -> bool:
        """Update mutable item fields and stamp the update time when changed."""
        changed = update_model(item, self._updatable_values(item_data))
        if changed:
            item.last_updated = updated_at
        return changed

    def _updatable_values(self, item_data: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in item_data.items()
            if key in self.item_columns - {"item_id", "created_at"}
        }


class KeywordItemLinkRepository:
    """Persistence operations for keyword-to-item discovery links."""

    def __init__(self, session: Optional[Any] = None):
        self.session = session or db.session

    def get(self, keyword_id: int, item_id: int) -> Optional[KeywordItems]:
        """Return one keyword-item link."""
        return KeywordItems.query.filter_by(
            keyword_id=keyword_id, item_id=item_id
        ).first()

    def create_if_missing(
        self,
        keyword_id: int,
        item_id: int,
        found_at: Optional[datetime] = None,
    ) -> Optional[KeywordItems]:
        """Create a keyword-item link unless it already exists."""
        if self.get(keyword_id, item_id):
            return None

        link = KeywordItems(keyword_id=keyword_id, item_id=item_id)
        if found_at is not None:
            link.found_at = found_at
        self.session.add(link)
        return link

    def list_for_keyword(self, keyword_id: int) -> list[KeywordItems]:
        """Return links for one keyword ordered by discovery time."""
        return (
            KeywordItems.query.filter_by(keyword_id=keyword_id)
            .order_by(KeywordItems.found_at.desc())
            .all()
        )


class SearchItemLinkRepository:
    """Persistence operations for saved-search-to-item links."""

    def __init__(self, session: Optional[Any] = None):
        self.session = session or db.session

    def get(self, query_id: Any, item_id: int) -> Optional[UserQueryItems]:
        """Return one saved-search item link."""
        return UserQueryItems.query.filter_by(
            query_id=query_id, item_id=item_id
        ).first()

    def create_if_missing(
        self,
        query_id: Any,
        item_id: int,
        created_at: Optional[datetime] = None,
    ) -> Optional[UserQueryItems]:
        """Create a saved-search item link unless it already exists."""
        if self.get(query_id, item_id):
            return None

        link = UserQueryItems(
            query_id=query_id,
            item_id=item_id,
            auction_ending_notification_sent=False,
        )
        if created_at is not None:
            link.created_at = created_at
        self.session.add(link)
        return link

    def list_for_search(self, query_id: Any) -> list[UserQueryItems]:
        """Return item links for a saved search ordered newest first."""
        return (
            UserQueryItems.query.filter_by(query_id=query_id)
            .order_by(UserQueryItems.created_at.desc())
            .all()
        )


class ItemFeedbackRepository:
    """Persistence operations for legacy item relevance feedback."""

    def get(
        self, user_id: int, item_id: int, keyword_id: int
    ) -> Optional[ItemRelevanceFeedback]:
        """Return one feedback record."""
        return ItemRelevanceFeedback.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            keyword_id=keyword_id,
        ).one_or_none()


class ItemRepository:
    """Backward-compatible item repository facade used by search processing."""

    def __init__(self, session: Optional[Any] = None):
        self.session = session or db.session
        self.items = GlobalItemRepository(self.session)
        self.item_columns = self.items.item_columns
        self.keyword_links = KeywordItemLinkRepository(self.session)
        self.search_links = SearchItemLinkRepository(self.session)
        self.feedback = ItemFeedbackRepository()

    def get_by_ebay_id(self, ebay_id: str) -> Optional[Item]:
        """Return one item by eBay id."""
        return self.items.get_by_ebay_id(ebay_id)

    def get_feedback(
        self,
        user_id: int,
        item_id: int,
        keyword_id: int,
    ) -> Optional[ItemRelevanceFeedback]:
        """Return one legacy relevance feedback record."""
        return self.feedback.get(user_id, item_id, keyword_id)

    def create_item(self, item_data: dict[str, Any]) -> Item:
        """Create a global item from eBay payload data."""
        return self.items.create(item_data)

    def link_keyword(
        self,
        keyword_id: int,
        item_id: int,
        found_at: Optional[datetime] = None,
    ) -> Optional[KeywordItems]:
        """Create a keyword-item link unless it already exists."""
        return self.keyword_links.create_if_missing(keyword_id, item_id, found_at)

    def link_query(
        self,
        query_id: Any,
        item_id: int,
        created_at: Optional[datetime] = None,
    ) -> Optional[UserQueryItems]:
        """Create a saved-search item link unless it already exists."""
        return self.search_links.create_if_missing(query_id, item_id, created_at)

    def get_query_item(self, query_id: Any, item_id: int) -> Optional[UserQueryItems]:
        """Return one saved-search item link."""
        return self.search_links.get(query_id, item_id)

    def update_item(
        self, item: Item, item_data: dict[str, Any], updated_at: datetime
    ) -> bool:
        """Update a global item and return whether it changed."""
        return self.items.update(item, item_data, updated_at)
