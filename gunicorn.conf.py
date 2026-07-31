import multiprocessing
import os

# Gunicorn configuration file for production FastAPI deployment

# Server Socket
# Render injects $PORT (default 10000); fall back to 8000 for Docker/VPS.
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker Processes
# Recommended formula: (2 x number of cores) + 1
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
# Gunicorn internal errors go to error.log
errorlog = "logs/error.log"
# Access logs are handled directly by Nginx and our FastAPI middleware,
# so we disable Gunicorn's default access log to avoid log duplication and save performance.
accesslog = None
loglevel = "info"

# Process Naming
proc_name = "astromatch_api"

# Server Mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL/TLS is handled by Nginx proxy, so no certfile/keyfile are defined here.
