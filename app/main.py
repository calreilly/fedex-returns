import io
import zipfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

from . import config, db, fedex_client, importer

app = FastAPI(title="FedEx Return Labels")
STATIC = Path(__file__).parent / "static"


class Row(BaseModel):
    rma: str
    name: str
    email: str
    phone: str
    boxes: int
    method: str
    street: str
    city: str
    state: str
    zip: str


@app.get("/api/config")
def get_config():
    return {"mock": config.MOCK, "env": config.FEDEX_ENV}


@app.post("/api/import")
async def import_csv(file: UploadFile = File(...)):
    text = (await file.read()).decode("utf-8-sig")
    rows, mapping = importer.parse_csv(text)
    for r in rows:
        prev = db.get(r["rma"])
        r["already_done"] = bool(prev and prev["status"] == "done")
    return {"rows": rows, "mapping": mapping}


@app.post("/api/process")
def process(row: Row, force: bool = False):
    r = row.model_dump()
    errors = importer.validate(r)
    if errors:
        raise HTTPException(400, "; ".join(errors))
    prev = db.get(r["rma"])
    if prev and prev["status"] == "done" and not force:
        raise HTTPException(409, "Labels already created for this RMA")
    folder = config.LABEL_DIR / "".join(c for c in r["rma"] if c.isalnum() or c in "-_")
    folder.mkdir(parents=True, exist_ok=True)
    tracking, pickup = [], None
    try:
        for i in range(1, r["boxes"] + 1):
            trk, pdf = fedex_client.create_label(r, i)
            (folder / f"{trk}.pdf").write_bytes(pdf)
            tracking.append(trk)
        if r["method"] == "pickup":
            pickup = fedex_client.schedule_pickup(r)
    except Exception as e:  # keep partial tracking so nothing is lost
        db.save(r["rma"], r["name"], r["boxes"], r["method"], "error", tracking, pickup, str(e))
        raise HTTPException(502, f"{e} (labels made before failure: {len(tracking)})")
    db.save(r["rma"], r["name"], r["boxes"], r["method"], "done", tracking, pickup)
    return {"rma": r["rma"], "tracking": tracking, "pickup": pickup}


@app.get("/api/history")
def history():
    return db.history()


@app.get("/api/labels/{rma}.zip")
def download(rma: str):
    folder = config.LABEL_DIR / "".join(c for c in rma if c.isalnum() or c in "-_")
    if not folder.is_dir():
        raise HTTPException(404, "No labels")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for f in sorted(folder.glob("*.pdf")):
            z.write(f, f.name)
    return Response(buf.getvalue(), media_type="application/zip")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
