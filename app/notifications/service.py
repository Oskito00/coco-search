from app.models import User
from app.utils.notifications import NotificationManager


class EventNotificationService:
    def notify_search_events(self, query, result):
        user = User.query.get(query.user_id)
        if not user:
            return {"new_items": 0, "price_drops": 0, "auction_alerts": 0}

        prefs = user.notification_preferences
        query_text = query.keyword.keyword_text
        counts = {"new_items": 0, "price_drops": 0, "auction_alerts": 0}

        if result.new_items and prefs.get("new_items", True):
            counts["new_items"] = len(result.new_items)
            NotificationManager.send_item_notification(user, result.new_items, query_text)

        if result.price_drops and prefs.get("price_drops", True):
            counts["price_drops"] = len(result.price_drops)
            NotificationManager.send_price_drops(user, result.price_drops, query_text)

        if result.ending_auctions and prefs.get("auction_alerts", True):
            counts["auction_alerts"] = len(result.ending_auctions)
            NotificationManager.send_auction_alerts(user, result.ending_auctions, query_text)

        return counts
