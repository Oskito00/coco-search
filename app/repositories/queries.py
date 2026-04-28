from typing import Any, Optional

from app.extensions import db
from app.models import Keyword, UserQuery


class KeywordRepository:
    """Persistence operations for search keywords."""

    def __init__(self, session: Optional[Any] = None):
        self.session = session or db.session

    def get(self, keyword_id: int) -> Optional[Keyword]:
        """Return one keyword by id."""
        return self.session.get(Keyword, keyword_id)

    def find_by_text(self, keyword_text: str) -> Optional[Keyword]:
        """Return the first keyword with matching text."""
        return Keyword.query.filter_by(keyword_text=keyword_text).first()

    def get_or_create(self, keyword_text: str) -> Keyword:
        """Return an existing keyword or create one."""
        keyword = self.find_by_text(keyword_text)
        if keyword is not None:
            return keyword

        keyword = Keyword(keyword_text=keyword_text)
        self.session.add(keyword)
        self.session.flush()
        return keyword


class UserQueryRepository:
    """Persistence operations for saved searches backed by UserQuery."""

    def __init__(self, session: Optional[Any] = None):
        self.session = session or db.session
        self.keywords = KeywordRepository(self.session)

    def get(self, query_id: Any) -> Optional[UserQuery]:
        """Return one saved search by id."""
        return self.session.get(UserQuery, query_id)

    def get_active(self, query_id: Any) -> Optional[UserQuery]:
        """Return an active saved search or None."""
        query = self.get(query_id)
        if not query or not query.is_active:
            return None
        return query

    def get_keyword(self, keyword_id: int) -> Optional[Keyword]:
        """Return one keyword by id."""
        return self.keywords.get(keyword_id)

    def get_or_create_keyword(self, keyword_text: str) -> Keyword:
        """Return an existing keyword or create one."""
        return self.keywords.get_or_create(keyword_text)

    def list_active(self) -> list[UserQuery]:
        """Return all active saved searches."""
        return UserQuery.query.filter_by(is_active=True).all()

    def list_for_user(
        self, user_id: int, include_inactive: bool = False
    ) -> list[UserQuery]:
        """Return saved searches owned by one user."""
        query = UserQuery.query.filter_by(user_id=user_id)
        if not include_inactive:
            query = query.filter_by(is_active=True)
        return query.all()

    def create(
        self,
        user_id: int,
        keyword_id: int,
        marketplace: str = "EBAY_GB",
        **values: Any,
    ) -> UserQuery:
        """Create a saved search record."""
        saved_search = UserQuery(
            user_id=user_id,
            keyword_id=keyword_id,
            marketplace=marketplace,
            **values,
        )
        self.session.add(saved_search)
        self.session.flush()
        return saved_search
