import os
import sys
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

try:
    # Passenger/cPanel may inject a stale DJANGO_SETTINGS_MODULE value.
    # Force the production settings module for this entrypoint.
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.production"

    from config.wsgi import application  # noqa: E402
except Exception:
    error_log = BASE_DIR / "passenger_wsgi_error.log"
    error_log.write_text(traceback.format_exc())
    raise
