import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def env(name, default=""):
    return os.getenv(name, default)


# FedEx credentials. Sandbox is the default so nothing real is ever billed by accident.
FEDEX_ENV = env("FEDEX_ENV", "sandbox")  # "sandbox" or "production"
FEDEX_BASE = (
    "https://apis.fedex.com" if FEDEX_ENV == "production" else "https://apis-sandbox.fedex.com"
)
CLIENT_ID = env("FEDEX_CLIENT_ID")
CLIENT_SECRET = env("FEDEX_CLIENT_SECRET")
ACCOUNT_NUMBER = env("FEDEX_ACCOUNT_NUMBER")
SERVICE_TYPE = env("FEDEX_SERVICE_TYPE", "FEDEX_GROUND")

# Mock mode: generates fake labels/pickups so you can try the UI without keys.
MOCK = env("FEDEX_MOCK", "1" if not CLIENT_ID else "0") == "1"

# Fixed destination (your warehouse)
WAREHOUSE = {
    "company": env("WAREHOUSE_COMPANY", "Warehouse"),
    "contact": env("WAREHOUSE_CONTACT", "Returns Dept"),
    "phone": env("WAREHOUSE_PHONE", "5555555555"),
    "street": env("WAREHOUSE_STREET", "123 Main St"),
    "city": env("WAREHOUSE_CITY", "Memphis"),
    "state": env("WAREHOUSE_STATE", "TN"),
    "zip": env("WAREHOUSE_ZIP", "38116"),
}

# Standard box
BOX = {
    "weight_lb": float(env("BOX_WEIGHT_LB", "10")),
    "length": int(env("BOX_LENGTH_IN", "12")),
    "width": int(env("BOX_WIDTH_IN", "12")),
    "height": int(env("BOX_HEIGHT_IN", "12")),
}

PICKUP_START = env("PICKUP_READY_TIME", "09:00:00")
PICKUP_CLOSE = env("PICKUP_CLOSE_TIME", "17:00:00")

LABEL_DIR = ROOT / "labels"
DB_PATH = ROOT / "returns.db"
