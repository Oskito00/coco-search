from datetime import datetime

from app.extensions import db
from app.models import ItemRelevanceFeedback, UserQueryItems


class RelevanceFeedbackService:
    def record_item_feedback(self, user, query_id, item_id, feedback):
        user_query_item = UserQueryItems.query.get_or_404((query_id, item_id))
        if user_query_item.user_query.user_id != user.id:
            return None, False

        feedback_entry = ItemRelevanceFeedback.query.filter_by(
            user_id=user.id,
            item_id=user_query_item.item_id,
            keyword_id=user_query_item.user_query.keyword_id,
        ).first()

        is_relevant = feedback == "relevant"
        if feedback_entry:
            feedback_entry.is_relevant = is_relevant
            feedback_entry.required_keywords = user_query_item.user_query.required_keywords
            feedback_entry.excluded_keywords = user_query_item.user_query.excluded_keywords
        else:
            feedback_entry = ItemRelevanceFeedback(
                user_id=user.id,
                item_id=user_query_item.item_id,
                keyword_id=user_query_item.user_query.keyword_id,
                required_keywords=user_query_item.user_query.required_keywords,
                excluded_keywords=user_query_item.user_query.excluded_keywords,
                is_relevant=is_relevant,
                created_at=datetime.utcnow(),
            )
            db.session.add(feedback_entry)

        return user_query_item, True
