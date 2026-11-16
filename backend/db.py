import os
import time

import psycopg
from psycopg.rows import dict_row

from metric import LEGACY, measure

SCHEMA = """
CREATE TABLE IF NOT EXISTS trials (
    id BIGSERIAL PRIMARY KEY,
    lot_code TEXT NOT NULL UNIQUE,
    crop_name TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS beds (
    id BIGSERIAL PRIMARY KEY,
    trial_id BIGINT NOT NULL REFERENCES trials(id),
    bed_no INTEGER NOT NULL,
    sown INTEGER NOT NULL,
    sprouted INTEGER NOT NULL,
    moldy INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS publications (
    id BIGSERIAL PRIMARY KEY,
    trial_id BIGINT NOT NULL REFERENCES trials(id),
    protocol_version TEXT NOT NULL,
    tested INTEGER NOT NULL,
    excluded_mold INTEGER NOT NULL,
    sprouted INTEGER NOT NULL,
    rate_bp INTEGER NOT NULL,
    note TEXT NOT NULL,
    published_by TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)


def init_db():
    last_error = None
    for _ in range(30):
        try:
            with connect() as conn:
                conn.execute(SCHEMA)
                count = conn.execute("SELECT COUNT(*) AS n FROM trials").fetchone()["n"]
                if count == 0:
                    _seed(conn)
                conn.commit()
            return
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(1)
    raise last_error


def _add_trial(conn, lot_code, crop_name, status, beds):
    trial = conn.execute(
        "INSERT INTO trials (lot_code, crop_name, status) VALUES (%s, %s, %s) RETURNING id",
        (lot_code, crop_name, status),
    ).fetchone()
    for bed_no, sown, sprouted, moldy in beds:
        conn.execute(
            """
            INSERT INTO beds (trial_id, bed_no, sown, sprouted, moldy)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (trial["id"], bed_no, sown, sprouted, moldy),
        )
    return trial["id"]


def publish(conn, trial_id: int, username: str, protocol: str):
    beds = conn.execute(
        "SELECT sown, sprouted, moldy FROM beds WHERE trial_id = %s ORDER BY bed_no",
        (trial_id,),
    ).fetchall()
    if not beds:
        raise ValueError("这个批次还没有床次")
    result = measure(beds, protocol)
    row = conn.execute(
        """
        INSERT INTO publications (
            trial_id, protocol_version, tested, excluded_mold, sprouted, rate_bp, note, published_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            trial_id,
            result["protocol_version"],
            result["tested"],
            result["excluded_mold"],
            result["sprouted"],
            result["rate_bp"],
            result["note"],
            username,
        ),
    ).fetchone()
    if protocol != LEGACY:
        conn.execute("UPDATE trials SET status = %s WHERE id = %s", ("已按现行口径出数", trial_id))
    return row["id"]


def _seed(conn):
    wheat = _add_trial(
        conn,
        "WH-2408",
        "小麦",
        "已按现行口径出数",
        [(1, 100, 92, 3), (2, 100, 88, 5)],
    )
    publish(conn, wheat, "admin", "v2")
    rice = _add_trial(
        conn,
        "RC-2411",
        "水稻",
        "待按现行口径重算",
        [(1, 80, 70, 6), (2, 80, 64, 4)],
    )
    publish(conn, rice, "admin", LEGACY)
    conn.execute("UPDATE trials SET status = %s WHERE id = %s", ("待按现行口径重算", rice))
