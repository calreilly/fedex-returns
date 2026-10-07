"""Parse a Wufoo CSV export into validated return requests."""
import csv
import io
import re

# Accepted header keywords per field (case-insensitive substring match).
FIELD_HINTS = {
    "rma": ["rma"],
    "email": ["email"],
    "phone": ["phone"],
    "pickup_date": ["pickup date", "date"],
    "boxes": ["box", "number of", "quantity", "qty"],
    "method": ["pickup", "drop", "method", "schedule"],
    "city": ["city"],
    "state": ["state", "province"],
    "zip": ["zip", "postal"],
    "street": ["street", "address"],
    "name": ["name"],
}
# Order matters: specific fields first so "email address" isn't taken as street.
MATCH_ORDER = ["rma", "email", "phone", "pickup_date", "boxes", "method",
               "city", "state", "zip", "street", "name"]


def map_headers(headers):
    mapping, used = {}, set()
    for field in MATCH_ORDER:
        for h in headers:
            if h in used:
                continue
            if any(k in h.lower() for k in FIELD_HINTS[field]):
                mapping[field] = h
                used.add(h)
                break
    return mapping


def parse_method(value):
    v = (value or "").lower()
    return "pickup" if ("pick" in v or "schedule" in v) else "dropoff"


def validate(row):
    errors = []
    if not row["rma"]:
        errors.append("Missing RMA #")
    if not row["name"]:
        errors.append("Missing name")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", row["email"] or ""):
        errors.append("Invalid email")
    if len(row["phone"]) < 10:
        errors.append("Phone needs 10 digits")
    if not (1 <= row["boxes"] <= 50):
        errors.append("Boxes must be 1-50")
    for f in ("street", "city", "state", "zip"):
        if not row[f]:
            errors.append(f"Missing {f}")
    return errors


def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    mapping = map_headers(reader.fieldnames or [])
    rows = []
    for raw in reader:
        def g(f):
            return (raw.get(mapping.get(f, ""), "") or "").strip()
        boxes = int(re.sub(r"\D", "", g("boxes")) or 0)
        row = {
            "rma": g("rma"), "name": g("name"), "email": g("email"),
            "phone": re.sub(r"\D", "", g("phone"))[-10:],
            "boxes": boxes, "method": parse_method(g("method")),
            "street": g("street"), "city": g("city"),
            "state": g("state").upper()[:2], "zip": g("zip"),
        }
        row["errors"] = validate(row)
        rows.append(row)
    return rows, mapping
