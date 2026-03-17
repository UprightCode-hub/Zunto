#server/gunicorn_config.py
"""
Gunicorn configuration for Render Free Tier
Optimized for 512MB RAM limit
"""

                                      
workers = 1

                                 
worker_class = 'sync'

                    
timeout = 120
graceful_timeout = 30
keepalive = 5

                                             
preload_app = True

                                                      
max_requests = 500
max_requests_jitter = 50

                                                               
worker_tmp_dir = '/dev/shm'

                       
import os
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

         
accesslog = '-'
errorlog = '-'
loglevel = 'info'
