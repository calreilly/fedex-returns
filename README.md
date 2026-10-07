# FedEx Return Labels

Local web app: import a Wufoo CSV, review/edit rows, generate FedEx return labels (one per box) and schedule pickups.

## Setup
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # fill in warehouse + FedEx keys
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000. With no FedEx keys it runs in **mock mode** (fake labels) so you can try it.

## Real FedEx
1. Create a project at https://developer.fedex.com and get a Client ID/Secret (sandbox first).
2. Fill `.env`, keep `FEDEX_ENV=sandbox`, test, then switch to `production`.

## Notes
- One FedEx shipment (label) is created per box, tagged with `RMA <n> box i/N`.
- Pickups are requested for the next business day, 9:00-17:00 (configurable).
- Duplicate RMAs are blocked unless you confirm.
- Tests: `pytest`
