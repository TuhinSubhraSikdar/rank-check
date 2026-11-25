import hashlib

from django.core.cache import cache
from django.http import HttpResponse


class AuthRateLimitMiddleware:
    """Bound sensitive POSTs by direct peer address; proxy must overwrite REMOTE_ADDR."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and request.path.startswith(("/accounts/", "/admin/login/")):
            identity = request.META.get("REMOTE_ADDR", "unknown")
            key = "auth-rate:" + hashlib.sha256(identity.encode()).hexdigest()
            cache.add(key, 0, timeout=300)
            try:
                count = cache.incr(key)
            except ValueError:
                count = 1
                cache.set(key, count, 300)
            if count > 20:
                response = HttpResponse("Too many attempts. Please try again in five minutes.", status=429)
                response["Retry-After"] = "300"
                return response
        return self.get_response(request)
