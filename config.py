import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Database
DB_PATH = DATA_DIR / "hermes.db"

# Flask config
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")
SSO_SECRET = os.getenv("SSO_SECRET", "sso-shared-secret-change-in-production")

# PIN Authentication
# Default PIN is 123456 - CHANGE THIS!
# To generate a new hash: python -c "from daemons.auth import hash_pin; print(hash_pin('YOUR_PIN'))"
PIN_HASH = os.getenv(
    "PIN_HASH",
    "6a66c2a5dc2d104757749f29623cc2b81f0ffdd57de22a0771e3742e13608196"
)

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"

# Port
PORT = 5003
