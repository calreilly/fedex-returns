from app import importer

CSV = """RMA #,Name,Email Address,Phone Number,Number of Boxes,Pickup or Drop-off,Street Address,City,State,Zip
1001,Jane Doe,jane@example.com,(555) 123-4567,2,Schedule a pickup,1 Elm St,Austin,tx,78701
1002,Bad Row,not-an-email,123,0,Drop off at FedEx,,,,
"""


def test_parse_valid_row():
    rows, _ = importer.parse_csv(CSV)
    r = rows[0]
    assert r["rma"] == "1001" and r["boxes"] == 2
    assert r["phone"] == "5551234567" and r["state"] == "TX"
    assert r["method"] == "pickup" and r["errors"] == []


def test_parse_invalid_row():
    rows, _ = importer.parse_csv(CSV)
    r = rows[1]
    assert r["method"] == "dropoff"
    assert "Invalid email" in r["errors"] and "Boxes must be 1-50" in r["errors"]
