from app._scheduler.sync import ScheduledJobSynchronizer
from app.extensions import scheduler


@scheduler.task(
    "interval",
    id="sync_jobs",
    minutes=1,  # ← Keep this
    max_instances=1,
)
def sync_jobs():
    with scheduler.app.app_context():
        ScheduledJobSynchronizer().sync()
