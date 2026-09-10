import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("fitdeals.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id TEXT UNIQUE,
        title TEXT NOT NULL,
        price REAL,
        original_price REAL,
        discount REAL,
        permalink TEXT,
        affiliate_url TEXT,
        thumbnail TEXT,
        source_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS publications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offer_id INTEGER,
        channel TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(offer_id) REFERENCES offers(id)
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS oauth_state (
        state TEXT PRIMARY KEY,
        code_verifier TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS oauth_tokens (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        access_token TEXT NOT NULL,
        refresh_token TEXT,
        user_id TEXT,
        expires_at INTEGER,
        updated_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def save_offer(data):
    conn = get_conn()
    now = now_iso()
    conn.execute("""
        INSERT INTO offers (
            item_id,title,price,original_price,discount,permalink,
            affiliate_url,thumbnail,source_json,created_at,updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(item_id) DO UPDATE SET
            title=excluded.title,
            price=excluded.price,
            original_price=excluded.original_price,
            discount=excluded.discount,
            permalink=excluded.permalink,
            affiliate_url=excluded.affiliate_url,
            thumbnail=excluded.thumbnail,
            source_json=excluded.source_json,
            updated_at=excluded.updated_at
    """, (
        data.get("item_id"), data.get("title"), data.get("price"),
        data.get("original_price"), data.get("discount"),
        data.get("permalink"), data.get("affiliate_url"),
        data.get("thumbnail"), json.dumps(data.get("source_json", {}), ensure_ascii=False),
        now, now
    ))
    conn.commit()
    row = conn.execute("SELECT * FROM offers WHERE item_id=?", (data.get("item_id"),)).fetchone()
    conn.close()
    return dict(row)

def list_offers(limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM offers ORDER BY COALESCE(discount,0) DESC, updated_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_offer(offer_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM offers WHERE id=?", (offer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def save_publication(offer_id, channel, message, status="manual"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO publications(offer_id,channel,message,status,created_at) VALUES(?,?,?,?,?)",
        (offer_id, channel, message, status, now_iso())
    )
    conn.commit()
    conn.close()

def list_publications(limit=30):
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.*, o.title
        FROM publications p
        LEFT JOIN offers o ON o.id = p.offer_id
        ORDER BY p.id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_oauth_state(state, code_verifier=None):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO oauth_state(state,code_verifier,created_at) VALUES(?,?,?)",
        (state, code_verifier, now_iso())
    )
    conn.commit()
    conn.close()

def pop_oauth_state(state):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM oauth_state WHERE state=?", (state,)
    ).fetchone()
    conn.execute("DELETE FROM oauth_state WHERE state=?", (state,))
    conn.commit()
    conn.close()
    return dict(row) if row else None

def save_tokens(access_token, refresh_token, user_id, expires_at):
    conn = get_conn()
    conn.execute("""
        INSERT INTO oauth_tokens(id,access_token,refresh_token,user_id,expires_at,updated_at)
        VALUES(1,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            access_token=excluded.access_token,
            refresh_token=excluded.refresh_token,
            user_id=excluded.user_id,
            expires_at=excluded.expires_at,
            updated_at=excluded.updated_at
    """, (access_token, refresh_token, user_id, expires_at, now_iso()))
    conn.commit()
    conn.close()

def get_tokens():
    conn = get_conn()
    row = conn.execute("SELECT * FROM oauth_tokens WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else None
