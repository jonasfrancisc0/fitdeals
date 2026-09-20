import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB = Path("fitdeals.db")


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    c = conn()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS offers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT UNIQUE,
            title TEXT,
            price REAL,
            original_price REAL,
            discount REAL,
            score REAL,
            permalink TEXT,
            affiliate_url TEXT,
            thumbnail TEXT,
            source_json TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS publications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER,
            channel TEXT,
            message TEXT,
            status TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS oauth_state(
            state TEXT PRIMARY KEY,
            code_verifier TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS oauth_tokens(
            id INTEGER PRIMARY KEY CHECK(id=1),
            access_token TEXT,
            refresh_token TEXT,
            user_id TEXT,
            expires_at INTEGER,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS collection_runs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            candidates INTEGER DEFAULT 0,
            price_calls INTEGER DEFAULT 0,
            offers_found INTEGER DEFAULT 0,
            diagnostics_json TEXT
        );
        """
    )
    c.commit()
    c.close()


def save_offer(o: dict[str, Any]) -> None:
    c = conn()
    n = now()
    c.execute(
        """
        INSERT INTO offers(
            item_id,title,price,original_price,discount,score,permalink,
            affiliate_url,thumbnail,source_json,created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(item_id) DO UPDATE SET
            title=excluded.title,
            price=excluded.price,
            original_price=excluded.original_price,
            discount=excluded.discount,
            score=excluded.score,
            permalink=excluded.permalink,
            affiliate_url=excluded.affiliate_url,
            thumbnail=excluded.thumbnail,
            source_json=excluded.source_json,
            updated_at=excluded.updated_at
        """,
        (
            o["item_id"], o["title"], o["price"], o.get("original_price"),
            o["discount"], o["score"], o.get("permalink", ""),
            o.get("affiliate_url", ""), o.get("thumbnail", ""),
            json.dumps(o.get("source_json", {}), ensure_ascii=False), n, n,
        ),
    )
    c.commit()
    c.close()


def offers(limit: int = 100) -> list[dict[str, Any]]:
    c = conn()
    r = c.execute(
        "SELECT * FROM offers ORDER BY score DESC, discount DESC, updated_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    c.close()
    return [dict(x) for x in r]


def offer(oid: int) -> dict[str, Any] | None:
    c = conn()
    r = c.execute("SELECT * FROM offers WHERE id=?", (oid,)).fetchone()
    c.close()
    return dict(r) if r else None


def pubs(limit: int = 30) -> list[dict[str, Any]]:
    c = conn()
    r = c.execute(
        "SELECT p.*,o.title FROM publications p LEFT JOIN offers o ON o.id=p.offer_id ORDER BY p.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    c.close()
    return [dict(x) for x in r]


def save_pub(oid: int, msg: str) -> None:
    c = conn()
    c.execute(
        "INSERT INTO publications(offer_id,channel,message,status,created_at) VALUES(?,?,?,?,?)",
        (oid, "manual", msg, "manual", now()),
    )
    c.commit()
    c.close()


def save_state(state: str, verifier: str | None) -> None:
    c = conn()
    c.execute("INSERT OR REPLACE INTO oauth_state VALUES(?,?,?)", (state, verifier, now()))
    c.commit()
    c.close()


def pop_state(state: str) -> dict[str, Any] | None:
    c = conn()
    r = c.execute("SELECT * FROM oauth_state WHERE state=?", (state,)).fetchone()
    c.execute("DELETE FROM oauth_state WHERE state=?", (state,))
    c.commit()
    c.close()
    return dict(r) if r else None


def save_tokens(access_token: str, refresh_token: str | None, user_id: str, expires_at: int) -> None:
    c = conn()
    c.execute(
        """
        INSERT INTO oauth_tokens VALUES(1,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            access_token=excluded.access_token,
            refresh_token=excluded.refresh_token,
            user_id=excluded.user_id,
            expires_at=excluded.expires_at,
            updated_at=excluded.updated_at
        """,
        (access_token, refresh_token, user_id, expires_at, now()),
    )
    c.commit()
    c.close()


def tokens() -> dict[str, Any] | None:
    c = conn()
    r = c.execute("SELECT * FROM oauth_tokens WHERE id=1").fetchone()
    c.close()
    return dict(r) if r else None


def save_collection_run(status: str, candidates: int, price_calls: int, offers_found: int, diagnostics: dict[str, Any], started_at: str, finished_at: str) -> None:
    c = conn()
    c.execute(
        "INSERT INTO collection_runs(started_at,finished_at,status,candidates,price_calls,offers_found,diagnostics_json) VALUES(?,?,?,?,?,?,?)",
        (started_at, finished_at, status, candidates, price_calls, offers_found, json.dumps(diagnostics, ensure_ascii=False)),
    )
    c.commit()
    c.close()


def last_run() -> dict[str, Any] | None:
    c = conn()
    r = c.execute("SELECT * FROM collection_runs ORDER BY id DESC LIMIT 1").fetchone()
    c.close()
    if not r:
        return None
    d = dict(r)
    try:
        d["diagnostics"] = json.loads(d.pop("diagnostics_json") or "{}")
    except json.JSONDecodeError:
        d["diagnostics"] = {}
    return d
