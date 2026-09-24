"""
Django settings for portfolio_site project.

Uses python-decouple for environment variable management.

The same Docker image runs in two modes:
- Public (default): read-only site behind CloudFront. Admin and dashboard URLs
  are not routed at all (see ENABLE_ADMIN in urls.py).
- Admin (ENABLE_ADMIN=True, TUNNEL_MODE=True): bound to 127.0.0.1 on the instance
  and reached only through an SSM port-forwarding session.
"""

from pathlib import Path

from decouple import Csv, config

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ──────────────────────────────────────────────
# Security
# ──────────────────────────────────────────────
DEBUG = config("DEBUG", default=False, cast=bool)

if DEBUG:
    SECRET_KEY = config("SECRET_KEY", default="insecure-dev-key-change-me")
else:
    # No fallback in production: the app refuses to start without a real key
    SECRET_KEY = config("SECRET_KEY")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# Admin and dashboard URLs are only routed when this is True (on by default locally)
ENABLE_ADMIN = config("ENABLE_ADMIN", default=DEBUG, cast=bool)

# True only for the admin container, reached at http://localhost through the SSM tunnel
TUNNEL_MODE = config("TUNNEL_MODE", default=False, cast=bool)

# ──────────────────────────────────────────────
# Application definition
# ──────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "axes",  # locks the login after repeated failed attempts
    "django_cleanup.apps.CleanupConfig",  # auto-delete orphaned media files
    # Local
    "projects.apps.ProjectsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serve static in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",  # must be last
]

ROOT_URLCONF = "portfolio_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "portfolio_site.wsgi.application"

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
# Use PostgreSQL in production, SQLite for local development
if config("USE_POSTGRES", default=False, cast=bool):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="portfolio_db"),
            "USER": config("DB_USER", default="portfolio_app"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ──────────────────────────────────────────────
# Authentication and login protection
# ──────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 14},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # must be first
    "django.contrib.auth.backends.ModelBackend",
]

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_RESET_ON_SUCCESS = True
# Lock on either the IP or the username. There is only one account and every tunnel
# request comes from the same local IP, so either rule simply locks the login.
AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]

LOGIN_URL = "/dashboard/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# ──────────────────────────────────────────────
# Internationalization
# ──────────────────────────────────────────────
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────
# Static files (CSS, JavaScript, Images) - baked into the image, served by WhiteNoise
# ──────────────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ──────────────────────────────────────────────
# Media files (user uploads)
# ──────────────────────────────────────────────
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

MEDIA_BUCKET = config("MEDIA_BUCKET", default="")
CLOUDFRONT_DOMAIN = config("CLOUDFRONT_DOMAIN", default="")

if MEDIA_BUCKET:
    # Production: uploads go to a private S3 bucket using the instance role
    # (no access keys) and are served to visitors through CloudFront with OAC.
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": MEDIA_BUCKET,
            "region_name": config("AWS_REGION", default="eu-west-2"),
            "location": "media",
            "custom_domain": CLOUDFRONT_DOMAIN,
            "querystring_auth": False,
            "file_overwrite": False,
            "default_acl": None,
        },
    }
    MEDIA_URL = f"https://{CLOUDFRONT_DOMAIN}/media/"

# ──────────────────────────────────────────────
# Default primary key field type
# ──────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ──────────────────────────────────────────────
# Logging - to stdout so Docker (and CloudWatch, if added) can collect it
# ──────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "axes": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

# ──────────────────────────────────────────────
# Production hardening (only when DEBUG=False)
# ──────────────────────────────────────────────
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_AGE = 60 * 60  # 1 hour
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True

    if TUNNEL_MODE:
        # Admin container: reached at http://localhost through the SSM tunnel, which is
        # already encrypted and IAM-authenticated. An HTTPS redirect or Secure-only
        # cookies would break login over localhost.
        SECURE_SSL_REDIRECT = False
        SESSION_COOKIE_SECURE = False
        CSRF_COOKIE_SECURE = False
    else:
        # Public container: CloudFront terminates TLS and passes the original scheme
        # in the CloudFront-Forwarded-Proto header (add it to the origin request policy).
        SECURE_PROXY_SSL_HEADER = ("HTTP_CLOUDFRONT_FORWARDED_PROTO", "https")
        SECURE_SSL_REDIRECT = True
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
        SECURE_HSTS_SECONDS = 31_536_000
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        # Preload only applies to a domain you own, not *.cloudfront.net
        SECURE_HSTS_PRELOAD = False

# HSTS preload intentionally off: the site runs on *.cloudfront.net, which cannot be
# submitted to the browser preload list. Revisit if a custom domain is added.
SILENCED_SYSTEM_CHECKS = ["security.W021"]