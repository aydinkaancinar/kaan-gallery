"""Local SQLite settings with optional private R2 connection."""
from .settings_base import *  # noqa: F403

# Optional private local connection file; deployment environment takes precedence.
# This file contains only the Django storage credential, never management secrets.
_local_storage_path = BASE_DIR / ".artwork-storage.json"
_local_storage = {}
if not os.environ.get("ARTWORK_GATEWAY_URL") and _local_storage_path.exists():
    _local_storage = json.loads(_local_storage_path.read_text())
_gateway_url = os.environ.get("ARTWORK_GATEWAY_URL") or _local_storage.get("url")
_gateway_token = os.environ.get("ARTWORK_GATEWAY_TOKEN") or _local_storage.get("token", "")
if _gateway_url:
    STORAGES = {
        "default": {
            "BACKEND": "items.storage_gateway.QuotaGatewayStorage",
            "OPTIONS": {
                "base_url": _gateway_url,
                "token": _gateway_token,
            },
        },
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
