from app.extensions import scheduler
from app.models import UserQuery
from app._scheduler.job_manager import add_query_jobs, remove_query_jobs

@scheduler.task(
    "interval",
    id="sync_jobs",
    minutes=1,
    max_instances=1
)
def sync_jobs():
    with scheduler.app.app_context():
        # Get active query UUIDs
        active = {str(q.query_id) for q in UserQuery.query.filter_by(is_active=True).all()}
        print(f"SYNC_JOBS: Active queries: {len(active)}")
        # Get scheduled UUIDs from job IDs
        scheduled = set()
        for job in scheduler.get_jobs():
            if job.id.startswith('query_'):
                parts = job.id.split('_')
                if len(parts) >= 3:
                    uuid_str = '_'.join(parts[1:-1])  # Handle UUIDs with underscores
                    scheduled.add(uuid_str)
        print(f"SYNC_JOBS: Scheduled queries: {len(scheduled)}")
        
        # Add missing jobs
        for qid in active - scheduled:
            print(f"SYNC_JOBS: Adding job for query {qid}")
            add_query_jobs(qid)
            
        # Remove deleted jobs
        for qid in scheduled - active:
            print(f"SYNC_JOBS: Removing job for query {qid}")
            remove_query_jobs(qid)