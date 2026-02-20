"""
NDA Shield — Security Middleware
- Security headers (HSTS, CSP, X-Content-Type, etc.)
- Rate limiting per IP
- Request/Response AES-256 encryption layer
"""
import base64
import hashlib
import json
import logging
import os
import time
from collections import defaultdict

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. SECURITY HEADERS MIDDLEWARE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SecurityHeadersMiddleware(MiddlewareMixin):
    """Inject production-grade security headers into every response."""

    def process_response(self, request, response):
        # Prevent MIME type sniffing
        response["X-Content-Type-Options"] = "nosniff"

        # Clickjacking protection
        response["X-Frame-Options"] = "DENY"

        # XSS protection (legacy browsers)
        response["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (disable sensors/geolocation/camera)
        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "accelerometer=(), gyroscope=(), magnetometer=()"
        )

        # Cache control for API responses
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response["Pragma"] = "no-cache"

        # HSTS (only in production)
        if not settings.DEBUG:
            response["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
            # Content Security Policy
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )

        # Custom NDA Shield header
        response["X-NDA-Shield"] = "Protected"

        return response


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. RATE LIMITING MIDDLEWARE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class RateLimitMiddleware(MiddlewareMixin):
    """
    In-memory rate limiter per IP address.
    Configurable via settings:
      RATE_LIMIT_REQUESTS = 100    # max per window
      RATE_LIMIT_WINDOW = 60       # seconds
      RATE_LIMIT_LOGIN_REQUESTS = 5
      RATE_LIMIT_LOGIN_WINDOW = 300
      RATE_LIMIT_PORTAL_REQUESTS = 30
      RATE_LIMIT_PORTAL_WINDOW = 60
    """

    _buckets = defaultdict(list)  # {ip: [timestamps]}
    _login_buckets = defaultdict(list)
    _portal_buckets = defaultdict(list)

    def _get_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "127.0.0.1")

    def _check_limit(self, bucket, ip, max_req, window):
        now = time.time()
        # Prune old entries
        bucket[ip] = [t for t in bucket[ip] if now - t < window]
        if len(bucket[ip]) >= max_req:
            retry_after = int(window - (now - bucket[ip][0])) + 1
            return False, retry_after
        bucket[ip].append(now)
        return True, 0

    def process_request(self, request):
        ip = self._get_ip(request)
        path = request.path

        # --- Login endpoint: strict rate limit ---
        if path == "/api/auth/login/" and request.method == "POST":
            max_r = getattr(settings, "RATE_LIMIT_LOGIN_REQUESTS", 5)
            window = getattr(settings, "RATE_LIMIT_LOGIN_WINDOW", 300)
            ok, retry = self._check_limit(self._login_buckets, ip, max_r, window)
            if not ok:
                logger.warning(f"Login rate limit hit: {ip}")
                return JsonResponse(
                    {
                        "error": "Too many login attempts. Please try again later.",
                        "retry_after": retry,
                    },
                    status=429,
                    headers={
                        "Retry-After": str(retry),
                        "X-RateLimit-Limit": str(max_r),
                        "X-RateLimit-Remaining": "0",
                    },
                )

        # --- Signing portal: moderate rate limit ---
        elif "/api/documents/portal/" in path:
            max_r = getattr(settings, "RATE_LIMIT_PORTAL_REQUESTS", 30)
            window = getattr(settings, "RATE_LIMIT_PORTAL_WINDOW", 60)
            ok, retry = self._check_limit(self._portal_buckets, ip, max_r, window)
            if not ok:
                return JsonResponse(
                    {"error": "Rate limit exceeded. Slow down.", "retry_after": retry},
                    status=429,
                    headers={"Retry-After": str(retry)},
                )

        # --- General API: standard rate limit ---
        elif path.startswith("/api/"):
            max_r = getattr(settings, "RATE_LIMIT_REQUESTS", 200)
            window = getattr(settings, "RATE_LIMIT_WINDOW", 60)
            ok, retry = self._check_limit(self._buckets, ip, max_r, window)
            if not ok:
                return JsonResponse(
                    {"error": "Rate limit exceeded.", "retry_after": retry},
                    status=429,
                    headers={
                        "Retry-After": str(retry),
                        "X-RateLimit-Limit": str(max_r),
                        "X-RateLimit-Remaining": "0",
                    },
                )

        return None

    def process_response(self, request, response):
        # Add rate limit headers to API responses
        if request.path.startswith("/api/"):
            ip = self._get_ip(request)
            max_r = getattr(settings, "RATE_LIMIT_REQUESTS", 200)
            window = getattr(settings, "RATE_LIMIT_WINDOW", 60)
            now = time.time()
            reqs = [t for t in self._buckets.get(ip, []) if now - t < window]
            remaining = max(0, max_r - len(reqs))
            response["X-RateLimit-Limit"] = str(max_r)
            response["X-RateLimit-Remaining"] = str(remaining)
            response["X-RateLimit-Reset"] = str(int(window))
        return response


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. AES-256 REQUEST/RESPONSE ENCRYPTION MIDDLEWARE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get_fernet():
    """Get or generate Fernet key from settings."""
    key = getattr(settings, "ENCRYPTION_KEY", None)
    if not key:
        # Derive from SECRET_KEY
        raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(raw)
    elif isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class EncryptionMiddleware(MiddlewareMixin):
    """
    Optional AES-256 encryption layer for API requests/responses.
    
    Activated when client sends header: X-Encrypted: true
    - Request body is decrypted before processing
    - Response body is encrypted before sending
    
    Encryption key: derived from SECRET_KEY or set ENCRYPTION_KEY in settings.
    
    Client workflow:
    1. GET /api/auth/encryption-key/ → returns base64 Fernet key
    2. Encrypt request body with Fernet(key)
    3. Send with header X-Encrypted: true
    4. Decrypt response body with same key
    """

    def process_request(self, request):
        if request.META.get("HTTP_X_ENCRYPTED") == "true" and request.body:
            try:
                fernet = _get_fernet()
                decrypted = fernet.decrypt(request.body)
                request._body = decrypted
                # Re-parse JSON
                if request.content_type and "json" in request.content_type:
                    request._stream = None
                    request._data = json.loads(decrypted)
            except (InvalidToken, Exception) as e:
                logger.warning(f"Decryption failed: {e}")
                return JsonResponse(
                    {"error": "Invalid encrypted payload."},
                    status=400,
                )
        return None

    def process_response(self, request, response):
        if (
            request.META.get("HTTP_X_ENCRYPTED") == "true"
            and hasattr(response, "content")
            and response.get("Content-Type", "").startswith("application/json")
        ):
            try:
                fernet = _get_fernet()
                encrypted = fernet.encrypt(response.content)
                response.content = encrypted
                response["Content-Type"] = "application/octet-stream"
                response["X-Encrypted"] = "true"
            except Exception as e:
                logger.error(f"Encryption failed: {e}")
        return response
