from app.models import Keyword, UserQuery


class UserQueryRepository:
    def get_active(self, query_id):
        query = UserQuery.query.get(query_id)
        if not query or not query.is_active:
            return None
        return query

    def get_keyword(self, keyword_id):
        return Keyword.query.get(keyword_id)
