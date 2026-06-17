from pathlib import Path

from decouple import config

from .base import *  # noqa: F403,F401

DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in config(
        "ALLOWED_HOSTS",
        default="velocitycutzug.com,www.velocitycutzug.com,127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]

# Production database: MySQL / cPanel
DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.mysql"),
        "NAME": config("DB_NAME", default="velovkym_city"),
        "USER": config("DB_USER", default="velovkym_velocity"),
        "PASSWORD": config("DB_PASSWORD", default="jt@5UuT@es@4tap"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Security / HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "public" / "static"

# Uploaded files: employee photos, service photos, etc.
MEDIA_URL = "/media/"
MEDIA_ROOT = PROJECT_ROOT / "public" / "media"

# Allow Django media fallback on shared hosting if Apache does not serve /media/
SERVE_MEDIA_FILES = True

# Whitenoise for static files
if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# IMPORTANT:
# Django needs "default" storage for uploaded files like employee photos.
# Without this, uploads fail with:
# InvalidStorageError: Could not find config for 'default' in settings.STORAGES.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT,
            "base_url": MEDIA_URL,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
from pathlib import Path

from decouple import config

from .base import *  # noqa: F403,F401

DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in config(
        "ALLOWED_HOSTS",
        default="velocitycutzug.com,www.velocitycutzug.com,127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]

# Production database: MySQL/cPanel.
DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.mysql"),
        "NAME": config("DB_NAME", default="velovkym_city"),
        "USER": config("DB_USER", default="velovkym_velocity"),
        "PASSWORD": config("DB_PASSWORD", default="jt@5UuT@es@4tap"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=env_bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=env_bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

PROJECT_ROOT = Path(__file__).resolve().parents[2]

STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "public" / "static"

# Uploaded media such as employee/service photos must be stored under public/media
# so Namecheap/Passenger can serve them at /media/... just like /static/ files.
MEDIA_URL = config("MEDIA_URL", default="/media/")
MEDIA_ROOT = Path(config("MEDIA_ROOT", default=str(PROJECT_ROOT / "public" / "media")))

# Fallback: allow Django to serve media files on shared hosting when Apache does not
# automatically expose public/media. This is acceptable here for small staff photos.
SERVE_MEDIA_FILES = config("SERVE_MEDIA_FILES", default=True, cast=env_bool)

if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# Keep uploaded media files, such as employee photos, on the local filesystem.
# Without the `default` storage entry, Django raises:
# InvalidStorageError: Could not find config for 'default' in settings.STORAGES.
STORAGES["default"] = {
    "BACKEND": "django.core.files.storage.FileSystemStorage",
    "OPTIONS": {
        "location": MEDIA_ROOT,
        "base_url": MEDIA_URL,
    },
}

STORAGES["staticfiles"] = {
    "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
}
