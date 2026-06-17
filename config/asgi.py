import os

from django.core.asgi import get_asgi_application

# Keep ASGI consistent with WSGI on production deployments.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_asgi_application()