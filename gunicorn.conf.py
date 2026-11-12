import os

bind = f"0.0.0.0:{int(os.environ.get('PORT', '8000'))}"
workers = 1
worker_class = 'gthread'
threads = 4
timeout = 60
graceful_timeout = 30
accesslog = '-'
errorlog = '-'
max_requests = 1000
max_requests_jitter = 50
# Match the explicit trust configured in Django after ingress verification.
forwarded_allow_ips = '*' if os.environ.get('DJANGO_TRUST_PROXY_HEADERS') == 'true' else '127.0.0.1,::1'
