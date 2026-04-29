# `app/queue/` — Current State

RQ-based background workers plus an rq-scheduler driving the per-query
scrape cadences. There is no APScheduler embedded in the Flask process
anymore — the long-running work all runs out-of-process.

## Architecture

```
Flask app  ───── enqueue() ─────▶  Redis  ◀──── RQ worker (app/queue/worker.py)
                                             ◀── rq-scheduler (scheduler_loop.py)
```

Two queues:

- `QUEUE_SCRAPE` — runs `full_scrape(query_id)` and `recent_scrape(query_id)`.
- `QUEUE_DEFAULT` — anything else.

## Job functions

`jobs.py` is the public surface — every function here must be importable
by string (RQ pickles the function path, not the function).

| Job | Cadence | Calls |
|---|---|---|
| `full_scrape(query_id)` | every 24 h | `ScheduledQueryService().run_full_scrape` |
| `recent_scrape(query_id)` | every `query.check_interval` minutes | `ScheduledQueryService().run_recent_scrape` |
| `sync_active_queries()` | every 60 s | `reconcile_query_schedules()` |

Each job runs inside `with_app_context` (see `runtime.py`) so SQLAlchemy /
Flask-Mail / itsdangerous all have an app context to bind to.

## Per-query scheduling

`scheduling.py` wraps `rq_scheduler.Scheduler` and assigns deterministic
job ids:

```
query:<query_id>:full
query:<query_id>:recent
```

`reconcile_query_schedules()` walks every active `UserQuery`:

1. Skips queries whose scheduled jobs already exist.
2. Schedules the missing pair with the right interval.
3. Cancels stranded jobs whose query has been deleted / deactivated.

That reconciliation loop is itself enqueued by a separate periodic job, so
no in-process scheduler is needed.

## Connection + queues

- `connection.py::get_redis()` — process-singleton `Redis` client built
  from `REDIS_URL`.
- `queues.py::enqueue(queue_name, func, *args)` — small helper for
  consistent queue selection.
- `worker.py` — entrypoint used by `Procfile`'s worker process.
- `scheduler_loop.py` — entrypoint for the rq-scheduler process.

## Current package layout

```text
app/queue/
  __init__.py
  connection.py        (lazy Redis singleton)
  jobs.py              (full_scrape, recent_scrape, sync_active_queries)
  queues.py            (queue names + enqueue helper)
  runtime.py           (with_app_context decorator)
  scheduler_loop.py    (rq-scheduler entrypoint)
  scheduling.py        (per-query schedule reconciliation)
  worker.py            (RQ worker entrypoint)
```
