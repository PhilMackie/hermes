# Gunicorn configuration for Raspberry Pi
# Optimized for low memory (1GB RAM)

bind = "0.0.0.0:5003"
workers = 2
worker_class = "sync"
timeout = 30

# Logging
accesslog = "/opt/hermes/logs/access.log"
errorlog = "/opt/hermes/logs/error.log"
loglevel = "info"

# Memory optimization
max_requests = 1000
max_requests_jitter = 100
