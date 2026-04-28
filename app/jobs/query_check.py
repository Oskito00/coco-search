from app.extensions import db, scheduler
from app.searches.item_processor import process_items
from app.searches.scheduled import ScheduledQueryService


def full_scrape_job(query_id):
    with scheduler.app.app_context():
        try:
            ScheduledQueryService().run_full_scrape(query_id)
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
        finally:
            db.session.remove()


def recent_scrape_job(query_id):
    with scheduler.app.app_context():
        try:
            ScheduledQueryService().run_recent_scrape(query_id)
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
        finally:
            db.session.remove()


__all__ = ["full_scrape_job", "recent_scrape_job", "process_items"]
