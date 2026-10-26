from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STAGED_IMAGES_DIR = DATA_DIR / "staged_images"
DB_PATH = DATA_DIR / "sync_store.db"
BLOCKET_AUTH_STATE_PATH = DATA_DIR / "blocket_auth_state.json"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
STAGED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Tradera configuration
TRADERA_USER_ID = "2195678"
TRADERA_ALIAS = "odenplan-sales"
TRADERA_PROFILE_URL = f"https://www.tradera.com/profile/items/{TRADERA_USER_ID}/{TRADERA_ALIAS}"
TRADERA_AUTH_STATE_PATH = DATA_DIR / "tradera_auth_state.json"
TRADERA_LOGIN_URL = "https://www.tradera.com/login"
TRADERA_MY_PAGES_URL = "https://www.tradera.com/my-tradera/selling"

import os

# Blocket configuration
BLOCKET_USER_EMAIL = os.environ.get("BLOCKET_USER_EMAIL", "")
BLOCKET_BASE_URL = "https://www.blocket.se"
BLOCKET_NEW_AD_URL = "https://www.blocket.se/create-item/start"

# Facebook Marketplace configuration
FB_AUTH_STATE_PATH = DATA_DIR / "fb_auth_state.json"
FB_BASE_URL = "https://www.facebook.com"
FB_MARKETPLACE_CREATE_URL = "https://www.facebook.com/marketplace/create/item"
FB_DEFAULT_LOCATION = "Stockholm"

# Default request headers
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
