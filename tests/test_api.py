import os
os.environ["FEDEX_MOCK"] = "1"

from fastapi.testclient import TestClient
from app import config, main

config.DB_PATH = config.ROOT / "test_returns.db"
config.LABEL_DIR = config.ROOT / "test_labels"
client = TestClient(main.app)

ROW = dict(rma="T1", name="A B", email="a@b.co", phone="5551234567", boxes=3,
           method="pickup", street="1 St", city="Austin", state="TX", zip="78701")


def setup_function():
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()


def test_process_creates_labels_and_blocks_duplicates():
    r = client.post("/api/process", json=ROW)
    assert r.status_code == 200
    j = r.json()
    assert len(j["tracking"]) == 3 and j["pickup"]
    assert client.post("/api/process", json=ROW).status_code == 409
    assert client.post("/api/process?force=true", json=ROW).status_code == 200
    z = client.get("/api/labels/T1.zip")
    assert z.status_code == 200
