"""FedEx Ship + Pickup API wrapper (with a mock mode for demo/testing)."""
import base64
import datetime as dt
import time

import requests

from . import config

_token = {"value": None, "exp": 0}


class FedExError(Exception):
    pass


def _auth():
    if _token["value"] and time.time() < _token["exp"] - 60:
        return _token["value"]
    r = requests.post(
        f"{config.FEDEX_BASE}/oauth/token",
        data={"grant_type": "client_credentials",
              "client_id": config.CLIENT_ID, "client_secret": config.CLIENT_SECRET},
        timeout=30,
    )
    if r.status_code != 200:
        raise FedExError(f"FedEx auth failed: {r.text[:300]}")
    j = r.json()
    _token.update(value=j["access_token"], exp=time.time() + j.get("expires_in", 3600))
    return _token["value"]


def _post(path, payload):
    r = requests.post(
        f"{config.FEDEX_BASE}{path}", json=payload, timeout=60,
        headers={"Authorization": f"Bearer {_auth()}", "Content-Type": "application/json",
                 "X-locale": "en_US"},
    )
    if r.status_code >= 300:
        try:
            errs = r.json().get("errors", [])
        except ValueError:
            errs = []
        raise FedExError("; ".join(e.get("message", "") for e in errs) or r.text[:300])
    return r.json()


def _addr(street, city, state, zipc):
    return {"streetLines": [street], "city": city, "stateOrProvinceCode": state,
            "postalCode": zipc, "countryCode": "US"}


def build_ship_payload(row, box_no):
    """One return shipment (one label) for one box. Client address is the origin."""
    w, b = config.WAREHOUSE, config.BOX
    acct = {"value": config.ACCOUNT_NUMBER}
    return {
        "labelResponseOptions": "LABEL",
        "accountNumber": acct,
        "requestedShipment": {
            "shipper": {
                "contact": {"personName": row["name"], "phoneNumber": row["phone"],
                            "emailAddress": row["email"]},
                "address": _addr(row["street"], row["city"], row["state"], row["zip"]),
            },
            "recipients": [{
                "contact": {"personName": w["contact"], "companyName": w["company"],
                            "phoneNumber": w["phone"]},
                "address": _addr(w["street"], w["city"], w["state"], w["zip"]),
            }],
            "shipDatestamp": dt.date.today().isoformat(),
            "serviceType": config.SERVICE_TYPE,
            "packagingType": "YOUR_PACKAGING",
            "pickupType": "USE_SCHEDULED_PICKUP" if row["method"] == "pickup"
                          else "DROPOFF_AT_FEDEX_LOCATION",
            "shippingChargesPayment": {
                "paymentType": "SENDER",
                "payor": {"responsibleParty": {"accountNumber": acct}}},
            "shipmentSpecialServices": {
                "specialServiceTypes": ["RETURN_SHIPMENT"],
                "returnShipmentDetail": {"returnType": "PRINT_RETURN_LABEL"},
            },
            "labelSpecification": {"imageType": "PDF", "labelFormatType": "COMMON2D",
                                   "labelStockType": "PAPER_85X11_TOP_HALF_LABEL"},
            "requestedPackageLineItems": [{
                "weight": {"units": "LB", "value": b["weight_lb"]},
                "dimensions": {"length": b["length"], "width": b["width"],
                               "height": b["height"], "units": "IN"},
                "customerReferences": [
                    {"customerReferenceType": "CUSTOMER_REFERENCE",
                     "value": f'RMA {row["rma"]} box {box_no}/{row["boxes"]}'}],
            }],
        },
    }


def create_label(row, box_no):
    """Returns (tracking_number, pdf_bytes)."""
    if config.MOCK:
        trk = f"MOCK{abs(hash((row['rma'], box_no))) % 10**10:010d}"
        return trk, _mock_pdf(row, box_no, trk)
    j = _post("/ship/v1/shipments", build_ship_payload(row, box_no))
    piece = j["output"]["transactionShipments"][0]["pieceResponses"][0]
    doc = piece["packageDocuments"][0]
    if doc.get("encodedLabel"):
        pdf = base64.b64decode(doc["encodedLabel"])
    else:
        pdf = requests.get(doc["url"], timeout=60).content
    return piece["trackingNumber"], pdf


def next_business_day(d=None):
    d = (d or dt.date.today()) + dt.timedelta(days=1)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def schedule_pickup(row):
    """Returns pickup confirmation code."""
    date = next_business_day()
    if config.MOCK:
        return f"MOCKPU{date:%m%d}"
    payload = {
        "associatedAccountNumber": {"value": config.ACCOUNT_NUMBER},
        "originDetail": {
            "pickupLocation": {
                "contact": {"personName": row["name"], "phoneNumber": row["phone"]},
                "address": _addr(row["street"], row["city"], row["state"], row["zip"]),
            },
            "readyDateTimestamp": f"{date.isoformat()}T{config.PICKUP_START}",
            "customerCloseTime": config.PICKUP_CLOSE,
        },
        "carrierCode": "FDXG" if "GROUND" in config.SERVICE_TYPE else "FDXE",
        "packageCount": row["boxes"],
        "remarks": f'RMA {row["rma"]}',
    }
    return _post("/pickup/v1/pickups", payload)["output"]["pickupConfirmationCode"]


def _mock_pdf(row, box_no, trk):
    text = f"MOCK LABEL {trk} RMA {row['rma']} box {box_no}/{row['boxes']}"
    body = f"BT /F1 18 Tf 50 700 Td ({text}) Tj ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(body)} >>\nstream\n{body}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offs = "%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n"
    out += "".join(f"{o:010d} 00000 n \n" for o in offs)
    out += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF"
    return out.encode()
