from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .config import (
    APP_NAME, ADMIN_PASSWORD, MAX_PRICE, MIN_DISCOUNT, OFFERS_PER_RUN,
    PRICE_LOOKUPS_PER_RUN, REQUIRE_DISCOUNT, SEARCH_LIMIT_PER_QUERY, SEARCH_QUERIES,
)
from .mercadolivre import MercadoLivreClient
from .messages import build
from .oauth import build_url, exchange

BASE = Path(__file__).resolve().parent.parent
app = FastAPI(title=APP_NAME)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.on_event("startup")
def startup():
    db.init_db()


def admin_auth(key: str | None):
    if not key or key != ADMIN_PASSWORD:
        raise HTTPException(401, "Chave do painel inválida.")


@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE / "static/index.html").read_text(encoding="utf-8")


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME, "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/dashboard")
def dashboard(x_admin_key: str | None = Header(default=None)):
    admin_auth(x_admin_key)
    client = MercadoLivreClient()
    status = client.verify_connection()
    return {
        "connected": status.get("connected", False),
        "connection": status,
        "offers": db.offers(100),
        "publications": db.pubs(30),
        "last_run": db.last_run(),
    }


@app.get("/api/mercadolivre/status")
def ml_status(x_admin_key: str | None = Header(default=None)):
    admin_auth(x_admin_key)
    return MercadoLivreClient().verify_connection()


@app.get("/api/test-search")
def test_search(q: str = Query(default="creatina", min_length=2, max_length=80), x_admin_key: str | None = Header(default=None)):
    admin_auth(x_admin_key)
    client = MercadoLivreClient()
    try:
        results = client.search(q)
        return {
            "ok": True,
            "query": q,
            "count": len(results),
            "items": [
                {
                    "id": x.get("id"),
                    "title": x.get("title"),
                    "price": x.get("price"),
                    "original_price": x.get("original_price"),
                    "permalink": x.get("permalink"),
                }
                for x in results[:20]
            ],
        }
    except Exception as exc:
        return JSONResponse({"ok": False, "query": q, "error": str(exc)}, status_code=502)


@app.post("/api/collect")
def collect(x_admin_key: str | None = Header(default=None)):
    admin_auth(x_admin_key)
    client = MercadoLivreClient()
    started = datetime.now(timezone.utc).isoformat()
    try:
        out = client.collect()
        for item in out:
            db.save_offer(item)
        finished = datetime.now(timezone.utc).isoformat()
        diag = client.diagnostics()
        diag["offers_found"] = len(out)
        db.save_collection_run("success", client.unique_candidates, client.price_calls, len(out), diag, started, finished)
        return {
            "ok": True,
            "count": len(out),
            "diagnostics": diag,
            "message": "Busca concluída. Veja os detalhes do diagnóstico no painel.",
        }
    except Exception as exc:
        finished = datetime.now(timezone.utc).isoformat()
        diag = client.diagnostics()
        diag["fatal_error"] = str(exc)
        db.save_collection_run("error", client.unique_candidates, client.price_calls, 0, diag, started, finished)
        raise HTTPException(502, detail=diag)


@app.get("/api/debug")
def debug(x_admin_key: str | None = Header(default=None)):
    admin_auth(x_admin_key)
    connection = MercadoLivreClient().verify_connection()
    return {
        "connection": connection,
        "config": {
            "queries": SEARCH_QUERIES,
            "max_price": MAX_PRICE,
            "min_discount": MIN_DISCOUNT,
            "require_discount": REQUIRE_DISCOUNT,
            "offers_per_run": OFFERS_PER_RUN,
            "search_limit_per_query": SEARCH_LIMIT_PER_QUERY,
            "price_lookups_per_run": PRICE_LOOKUPS_PER_RUN,
        },
    }


@app.get("/api/offer/{oid}/message")
def message(
    oid: int,
    coupon: str | None = Query(default=None),
    x_admin_key: str | None = Header(default=None),
):
    admin_auth(x_admin_key)
    found = db.offer(oid)
    if not found:
        raise HTTPException(404, "Oferta não encontrada.")
    return {"message": build(found, coupon)}


@app.get("/auth/mercadolivre")
def login():
    try:
        return RedirectResponse(build_url())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, 400)


@app.get("/auth/mercadolivre/callback")
def callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return JSONResponse({"error": error}, 400)
    if not code or not state:
        return JSONResponse({"error": "Callback OAuth sem code/state. Entre pelo botão Conectar Mercado Livre."}, 400)
    try:
        exchange(code, state)
        return RedirectResponse("/")
    except Exception as exc:
        return JSONResponse({"error": "Falha no OAuth", "detail": str(exc)}, 400)
