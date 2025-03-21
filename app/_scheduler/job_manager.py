from datetime import datetime
from app.jobs.query_check import full_scrape_job, recent_scrape_job
from app.extensions import scheduler
from app.models import UserQuery

def add_query_jobs(query_id):
    print(f"ADD_QUERY_JOBS: Query ID: {query_id}")
    query = UserQuery.query.get(query_id)
    print(f"ADD_QUERY_JOBS: Query: {query}")
    # Full job - runs immediately and every 24h
    scheduler.add_job(
        func=full_scrape_job,
        trigger='interval',
        args=[query_id],
        hours=24,
        id=f'query_{query_id}_full',
        next_run_time=datetime.utcnow(),  # First run now
        misfire_grace_time=3600,  # 1 hour grace period
        coalesce=True  # Combine missed runs
    )
    
    # Recent job
    scheduler.add_job(
        func=recent_scrape_job,
        trigger='interval',
        minutes=query.check_interval,
        id=f'query_{query_id}_recent',
        args=[query_id]
    )
    
def remove_query_jobs(query_id):
    try:
        scheduler.remove_job(f'query_{query_id}_recent')
        scheduler.remove_job(f'query_{query_id}_full')
    except LookupError:
        pass