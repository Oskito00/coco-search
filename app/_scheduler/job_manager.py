from datetime import datetime, timezone

from tzlocal import get_localzone

from app.jobs.query_check import full_scrape_job, recent_scrape_job
from app.extensions import scheduler
from app.models import UserQuery
import pytz  # Import pytz for timezone handling

def add_query_jobs(query_id):
    query = UserQuery.query.get(query_id)

    query = UserQuery.query.get(query_id)
    print(f"ADD_QUERY_JOBS: Query: {query}")
    # Full job - runs immediately and every 24h

    # Get the system's local timezone
    local_tz = get_localzone()
    
    # Print debug info
    now = datetime.now(local_tz)
    print(f"System local timezone: {local_tz}")
    print(f"Current local time: {now}")
    print(f"Timezone name: {now.tzname()}")  # Will show 'BST' during summer in UK
    

    scheduler.add_job(
        func=full_scrape_job,
        trigger='interval',
        args=[query_id],
        hours=24,
        id=f'query_{query_id}_full',
        next_run_time=now,  # First run now
        misfire_grace_time=3600,  # 1 hour grace period
        coalesce=True  # Combine missed runs
    )
    
    # Recent job
    scheduler.add_job(
        func=recent_scrape_job,
        trigger='interval',
        minutes=query.check_interval,
        id=f'query_{query_id}_recent',
        args=[query_id],
    )
    
def remove_query_jobs(query_id):
    try:
        scheduler.remove_job(f'query_{query_id}_recent')
        scheduler.remove_job(f'query_{query_id}_full')
    except LookupError:
        pass