import os

from django.core.wsgi import get_wsgi_application

# Production hosting should always load production settings unless explicitly
# overridden before WSGI starts. This prevents uploads from accidentally using
# development paths such as BASE_DIR/media instead of public/media.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_wsgi_application()