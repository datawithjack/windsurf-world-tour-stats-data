"""
Gunicorn configuration for Windsurf World Tour Stats API

This file configures Gunicorn to run the FastAPI application in production.

Usage:
    gunicorn -c deployment/gunicorn.conf.py src.api.main:app
"""

import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"  # Bind to localhost (nginx will proxy)
backlog = 2048  # Maximum number of pending connections

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # Recommended: (2 x CPU cores) + 1
worker_class = "uvicorn.workers.UvicornWorker"  # Use Uvicorn workers for ASGI
worker_connections = 1000  # Maximum simultaneous clients per worker
max_requests = 1000  # Restart workers after this many requests (prevents memory leaks)
max_requests_jitter = 50  # Add randomness to max_requests
timeout = 120  # Workers silent for more than this many seconds are killed (increased from 60 to handle complex queries)
keepalive = 5  # Seconds to wait for requests on a Keep-Alive connection

# Logging
accesslog = "/var/log/gunicorn/windsurf-api-access.log"
errorlog = "/var/log/gunicorn/windsurf-api-error.log"
loglevel = "info"  # debug, info, warning, error, critical
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "windsurf-api"

# Server mechanics
daemon = False  # Don't daemonize (systemd will handle this)
pidfile = "/var/run/gunicorn/windsurf-api.pid"
user = None  # Run as current user (or set to specific user, e.g., 'www-data')
group = None
umask = 0
tmp_upload_dir = None

# SSL (if terminating SSL at Gunicorn instead of nginx)
# keyfile = None
# certfile = None

# Environment
raw_env = [
    f"API_ENV=production",
]

# Preload application code before worker processes are forked
preload_app = True

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print("Gunicorn master process starting")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("Gunicorn reloading")

def when_ready(server):
    """Called just after the server is started."""
    print(f"Gunicorn server is ready. Spawning {server.cfg.workers} workers")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    print(f"Worker {worker.pid} spawned")

def pre_exec(server):
    """Called just before a new master process is forked."""
    print("Forking new master process")

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    print(f"Worker {worker.pid} exited")
