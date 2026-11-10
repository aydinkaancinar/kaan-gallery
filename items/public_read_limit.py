"""Small, pre-view limits for anonymous public reads on the Render backend."""

import hashlib
import ipaddress
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

from .permissions import is_verified_staff


WINDOW_SECONDS = 60
LIMITS = {
    "image": (240, 1200),  # per client, then across this application process
    "catalog": (120, 600),
}


def client_ip(request):
    """Render places the actual client first in X-Forwarded-For."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    candidate = forwarded.split(",", 1)[0].strip() if getattr(
        settings, "PUBLIC_READ_LIMIT_TRUST_XFF", False
    ) else ""
    for value in (candidate, request.META.get("REMOTE_ADDR", "")):
        try:
            return ipaddress.ip_address(value).compressed
        except ValueError:
            continue
    return "unknown"


def increment(key, timeout):
    if cache.add(key, 1, timeout=timeout):
        return 1
    try:
        return cache.incr(key)
    except ValueError:  # A window can expire between add() and incr().
        cache.add(key, 1, timeout=timeout)
        return 1


class PublicReadLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "PUBLIC_READ_LIMIT_ENABLED", False) or request.method not in ("GET", "HEAD"):
            return self.get_response(request)

        path = request.path_info
        if path.startswith("/artwork-images/"):
            group = "image"
        elif path.startswith(("/items/", "/artworks/", "/artists/")):
            group = "catalog"
        else:
            return self.get_response(request)

        if is_verified_staff(request.user):
            return self.get_response(request)

        now = time.time()
        window = int(now // WINDOW_SECONDS)
        timeout = WINDOW_SECONDS * 2
        fingerprint = hashlib.sha256(client_ip(request).encode()).hexdigest()[:24]
        per_client, overall = LIMITS[group]
        per_client_count = increment(f"public-read:{group}:{window}:ip:{fingerprint}", timeout)
        total_count = increment(f"public-read:{group}:{window}:all", timeout)
        if per_client_count > per_client or total_count > overall:
            response = HttpResponse("Too many public requests. Try again shortly.", status=429)
            response["Retry-After"] = str(max(1, WINDOW_SECONDS - int(now % WINDOW_SECONDS)))
            response["Cache-Control"] = "no-store"
            return response
        return self.get_response(request)
