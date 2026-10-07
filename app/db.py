import json
import sqlite3
from . import config


def conn():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute(
        """CREATE TABLE IF NOT EXISTS returns (
        rma TEXT PRIMARY KEY, name TEXT, boxes INTEGER, method TEXT,
        status TEXT, tracking TEXT, pickup_confirmation TEXT, error TEXT,
        created TEXT DEFAULT CURRENT_TIMESTAMP)"""
    )
    return c


def get(rma):
    with conn() as c:
        return c.execute("SELECT * FROM returns WHERE rma=?", (rma,)).fetchone()


def save(rma, name, boxes, method, status, tracking=None, pickup=None, error=None):
    with conn() as c:
        c.execute(
            """INSERT OR REPLACE INTO returns
            (rma,name,boxes,method,status,tracking,pickup_confirmation,error)
            VALUES (?,?,?,?,?,?,?,?)""",
            (rma, name, boxes, method, status, json.dumps(tracking or []), pickup, error),
        )


def history():
    with conn() as c:
        rows = c.execute("SELECT * FROM returns ORDER BY created DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["tracking"] = json.loads(d["tracking"] or "[]")
        out.append(d)
    return out
