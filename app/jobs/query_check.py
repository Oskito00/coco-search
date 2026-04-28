from app.jobs.runtime import run_with_scheduler_context
from app.searches.item_processor import process_items
from app.searches.scheduled import ScheduledQueryService


def full_scrape_job(query_id):
    return run_with_scheduler_context(
        lambda: ScheduledQueryService().run_full_scrape(query_id)
    )


def recent_scrape_job(query_id):
    return run_with_scheduler_context(
        lambda: ScheduledQueryService().run_recent_scrape(query_id)
    )


__all__ = ["full_scrape_job", "recent_scrape_job", "process_items"]
