import hashlib
import base64
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,testserver","139.59.78.201:8001").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "oauth2_provider",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "accounts",
    "ndas",
    "people",
    "assignments",
    "documents",
]

MIDDLEWARE = [
    "nda_shield.middleware.SecurityHeadersMiddleware",
    "nda_shield.middleware.RateLimitMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "nda_shield.middleware.EncryptionMiddleware",
]

ROOT_URLCONF = "nda_shield.urls"
WSGI_APPLICATION = "nda_shield.wsgi.application"
AUTH_USER_MODEL = "accounts.User"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "oauth2_provider.backends.OAuth2Backend",
    "django.contrib.auth.backends.ModelBackend",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 200,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "nda_shield.exception_handler.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "200/minute",
    },
}

OAUTH2_PROVIDER = {
    "SCOPES": {"read": "Read", "write": "Write"},
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,
    "REFRESH_TOKEN_EXPIRE_SECONDS": 604800,
    "ROTATE_REFRESH_TOKEN": True,
}

CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept", "authorization", "content-type", "origin",
    "x-csrftoken", "x-requested-with", "x-encrypted",
]

# ── Security Settings ─────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 63072000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ── Rate Limiting ──────────────────────────────────────────
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "200"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_LOGIN_REQUESTS = int(os.getenv("RATE_LIMIT_LOGIN_REQUESTS", "5"))
RATE_LIMIT_LOGIN_WINDOW = int(os.getenv("RATE_LIMIT_LOGIN_WINDOW", "300"))
RATE_LIMIT_PORTAL_REQUESTS = int(os.getenv("RATE_LIMIT_PORTAL_REQUESTS", "30"))
RATE_LIMIT_PORTAL_WINDOW = int(os.getenv("RATE_LIMIT_PORTAL_WINDOW", "60"))

# ── Encryption ─────────────────────────────────────────────
_raw_key = hashlib.sha256(SECRET_KEY.encode()).digest()
ENCRYPTION_KEY = base64.urlsafe_b64encode(_raw_key)

# ── File Handling ──────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024

# ── Email ──────────────────────────────────────────────────
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "nda@cybersec.com")
EMAIL_SUBJECT_PREFIX = "[NDA Shield] "

# ── Spectacular ────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "NDA Shield API",
    "DESCRIPTION": "Cybersecurity NDA Management System",
    "VERSION": "3.1.0",
}

# ── App Settings ───────────────────────────────────────────
COMPANY_NAME = os.getenv("COMPANY_NAME", "CyberSec Corp")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
