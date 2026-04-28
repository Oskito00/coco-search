from sqlalchemy import inspect

from app.extensions import db
from app.models import Item, ItemRelevanceFeedback, KeywordItems, UserQueryItems


class ItemRepository:
    def __init__(self, session=None):
        self.session = session or db.session
        self.item_columns = {c.key for c in inspect(Item).mapper.column_attrs}

    def get_by_ebay_id(self, ebay_id):
        return Item.query.filter_by(ebay_id=ebay_id).first()

    def get_feedback(self, user_id, item_id, keyword_id):
        return ItemRelevanceFeedback.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            keyword_id=keyword_id,
        ).one_or_none()

    def create_item(self, item_data):
        valid_data = {k: v for k, v in item_data.items() if k in self.item_columns}
        item = Item(**valid_data)
        item.location_country = item_data.get("location", {}).get("country")
        item.postal_code = item_data.get("location", {}).get("postal_code")
        self.session.add(item)
        self.session.flush()
        return item

    def link_keyword(self, keyword_id, item_id, found_at=None):
        if KeywordItems.query.filter_by(keyword_id=keyword_id, item_id=item_id).first():
            return None

        link = KeywordItems(keyword_id=keyword_id, item_id=item_id)
        if found_at is not None:
            link.found_at = found_at
        self.session.add(link)
        return link

    def link_query(self, query_id, item_id, created_at=None):
        if UserQueryItems.query.filter_by(query_id=query_id, item_id=item_id).first():
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

    def get_query_item(self, query_id, item_id):
        return UserQueryItems.query.filter_by(query_id=query_id, item_id=item_id).first()

    def update_item(self, item, item_data, updated_at):
        changed = False
        for key in self.item_columns - {"item_id", "created_at"}:
            if key in item_data and getattr(item, key) != item_data[key]:
                setattr(item, key, item_data[key])
                changed = True

        if changed:
            item.last_updated = updated_at

        return changed
