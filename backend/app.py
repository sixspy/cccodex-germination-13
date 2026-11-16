import json
import os

from bottle import Bottle, request, response, run

from auth import authenticate, issue_token, read_user
from db import connect, init_db, publish
from metric import CURRENT, rate_label

app = Bottle()


def _json(payload, status=200):
    response.status = status
    response.content_type = "application/json; charset=utf-8"
    return json.dumps(payload, ensure_ascii=False)


def _user():
    return read_user(request.headers.get("Authorization"))


def _stamp(value):
    return value.isoformat(sep=" ", timespec="minutes") if value else None


def _trial_payload(conn, trial_id):
    trial = conn.execute(
        "SELECT id, lot_code, crop_name, status FROM trials WHERE id = %s",
        (trial_id,),
    ).fetchone()
    if not trial:
        return None
    beds = conn.execute(
        "SELECT bed_no, sown, sprouted, moldy FROM beds WHERE trial_id = %s ORDER BY bed_no",
        (trial_id,),
    ).fetchall()
    publications = conn.execute(
        """
        SELECT id, protocol_version, tested, excluded_mold, sprouted, rate_bp, note, published_by, published_at
        FROM publications WHERE trial_id = %s ORDER BY id DESC
        """,
        (trial_id,),
    ).fetchall()
    for row in publications:
        row["rate_label"] = rate_label(row["rate_bp"])
        row["published_at"] = _stamp(row["published_at"])
        row["current"] = row["protocol_version"] == CURRENT
    return {"trial": trial, "beds": beds, "publications": publications}


@app.get("/api/health")
def health():
    with connect() as conn:
        conn.execute("SELECT 1")
    return _json({"status": "ok", "service": "germination-protocol"})


@app.post("/api/login")
def login():
    try:
        body = json.loads(request.body.read() or b"{}")
    except json.JSONDecodeError:
        return _json({"detail": "请求不是合法的 JSON"}, 400)
    user = authenticate(str(body.get("username", "")).strip(), str(body.get("password", "")))
    if not user:
        return _json({"detail": "用户名或密码错误"}, 401)
    return _json(
        {
            "access_token": issue_token(user),
            "username": user["username"],
            "role": user["role"],
            "title": user["title"],
        }
    )


@app.get("/api/trials")
def list_trials():
    if not _user():
        return _json({"detail": "未登录"}, 401)
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, lot_code, crop_name, status FROM trials ORDER BY id"
        ).fetchall()
    return _json(rows)


@app.get("/api/trials/<trial_id:int>")
def trial_detail(trial_id):
    if not _user():
        return _json({"detail": "未登录"}, 401)
    with connect() as conn:
        payload = _trial_payload(conn, trial_id)
    if not payload:
        return _json({"detail": "没有这个批次"}, 404)
    return _json(payload)


@app.post("/api/trials/<trial_id:int>/publish")
def publish_current(trial_id):
    user = _user()
    if not user:
        return _json({"detail": "未登录"}, 401)
    if user["role"] != "writer":
        return _json({"detail": "见证员不能出数"}, 403)
    try:
        with connect() as conn:
            exists = conn.execute("SELECT id FROM trials WHERE id = %s", (trial_id,)).fetchone()
            if not exists:
                return _json({"detail": "没有这个批次"}, 404)
            publish(conn, trial_id, user["username"], CURRENT)
            payload = _trial_payload(conn, trial_id)
            conn.commit()
    except ValueError as exc:
        return _json({"detail": str(exc)}, 400)
    return _json(payload)


init_db()


if __name__ == "__main__":
    run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), server="waitress")
