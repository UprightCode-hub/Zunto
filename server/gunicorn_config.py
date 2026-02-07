"""
Gunicorn configuration for Render Free Tier
Optimized for 512MB RAM limit
"""

# Use only 1 worker to minimize memory
workers = 1

# Use sync worker (lowest memory)
worker_class = 'sync'

# Reasonable timeout
timeout = 120
graceful_timeout = 30
keepalive = 5

# Preload app to share memory between workers
preload_app = True

# Restart workers periodically to prevent memory leaks
max_requests = 500
max_requests_jitter = 50

# Use shared memory for temporary files (faster, less disk I/O)
worker_tmp_dir = '/dev/shm'

# Bind to Render's port
import os
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'