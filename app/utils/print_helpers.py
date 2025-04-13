def print_scheduler_settings(app, scheduler):
    """Print comprehensive scheduler settings for debugging"""
    print("\n==== SCHEDULER CONFIGURATION ====")
    
    # Basic scheduler settings
    print(f"Scheduler API enabled: {app.config.get('SCHEDULER_API_ENABLED', False)}")
    
    # Jobstore settings
    jobstores = app.config.get('SCHEDULER_JOBSTORES', {})
    print(f"Jobstore type: {jobstores.get('default', {}).get('type', 'Not configured')}")
    
    # Executor settings
    executors = app.config.get('SCHEDULER_EXECUTORS', {})
    executor = executors.get('default', {})
    print(f"Executor type: {executor.get('type', 'Not configured')}")
    print(f"Max workers: {executor.get('max_workers', 'Not configured')}")
    
    # Job defaults
    job_defaults = app.config.get('SCHEDULER_JOB_DEFAULTS', {})
    print(f"Coalesce: {job_defaults.get('coalesce', 'Not configured')}")
    print(f"Max instances: {job_defaults.get('max_instances', 'Not configured')}")
    print(f"Misfire grace time: {job_defaults.get('misfire_grace_time', 'Not configured')} seconds")
    
    # Timezone settings
    print(f"Scheduler timezone: {scheduler.timezone}")
    
    # Database connection pool
    db_options = app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})
    print("\n==== DATABASE CONNECTION POOL ====")
    print(f"Pool size: {db_options.get('pool_size', 'Not configured')}")
    print(f"Max overflow: {db_options.get('max_overflow', 'Not configured')}")
    print(f"Pool timeout: {db_options.get('pool_timeout', 'Not configured')} seconds")
    print(f"Pool recycle: {db_options.get('pool_recycle', 'Not configured')} seconds")
    print(f"Pool pre-ping: {db_options.get('pool_pre_ping', 'Not configured')}")
    
    print("\n==== CURRENT SCHEDULED JOBS ====")
    jobs = scheduler.get_jobs()
    print(f"Total scheduled jobs: {len(jobs)}")
    
    # Print categories of jobs
    job_types = {}
    for job in jobs:
        job_id = job.id
        job_type = 'other'
        
        if job_id.startswith('query_'):
            parts = job_id.split('_')
            if len(parts) > 2 and parts[-1] in ('full', 'recent'):
                job_type = f"query_{parts[-1]}"
        elif job_id == 'sync_jobs':
            job_type = 'sync_jobs'
            
        if job_type not in job_types:
            job_types[job_type] = 0
        job_types[job_type] += 1
    
    for job_type, count in job_types.items():
        print(f"{job_type}: {count} jobs")
    
    print("================================\n")