from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .config import APP_NAME, ADMIN_PASSWORD, ADMIN_USER
from .messages import build_message
from .mercadolivre import get_me
from .oauth import build_authorization_url, exchange_code, get_valid_access_token
from .scheduler import collect_once, start_scheduler

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title=APP_NAME)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.on_event("startup")
def startup():
    db.init_db()
    start_scheduler()

def require_admin(x_admin_key: str | None):
    if not x_admin_key or x_admin_key != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Chave do painel inválida.")

@app.get("/", response_class=HTMLResponse)
def index():
    return (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}

@app.get("/api/dashboard")
def dashboard(x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    tokens = db.get_tokens()
    return {
        "offers": db.list_offers(50),
        "publications": db.list_publications(30),
        "connected": bool(tokens and get_valid_access_token()),
    }

@app.post("/api/collect")
def manual_collect(x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    try:
        count = collect_once()
        return {"ok": True, "count": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/offer/{offer_id}/message")
def offer_message(
    offer_id: int,
    coupon: str | None = Query(default=None),
    x_admin_key: str | None = Header(default=None),
):
    require_admin(x_admin_key)
    offer = db.get_offer(offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Oferta não encontrada.")
    return {"message": build_message(offer, coupon=coupon)}

@app.post("/api/publication")
def publication(
    offer_id: int,
    message: str,
    channel: str = "manual",
    x_admin_key: str | None = Header(default=None),
):
    require_admin(x_admin_key)
    if channel != "manual":
        raise HTTPException(
            status_code=400,
            detail="V4 registra publicação manual. Não usa automação de WhatsApp Web."
        )
    db.save_publication(offer_id, channel, message, status="manual")
    return {"ok": True}

@app.get("/auth/mercadolivre")
def ml_login():
    try:
        return RedirectResponse(build_authorization_url())
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

@app.get("/auth/mercadolivre/callback")
def ml_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return JSONResponse({"error": f"Mercado Livre recusou a autorização: {error}"}, status_code=400)
    if not code or not state:
        return JSONResponse({"error": "Callback OAuth sem code/state."}, status_code=400)

    try:
        exchange_code(code, state)
        return RedirectResponse("/")
    except Exception as exc:
        return JSONResponse(
            {"error": "Falha ao concluir OAuth.", "detail": str(exc)},
            status_code=400,
        )

@app.get("/api/mercadolivre/status")
def ml_status(x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    tokens = db.get_tokens()
    if not tokens:
        return {"connected": False}
    return {
        "connected": bool(get_valid_access_token()),
        "user_id": tokens.get("user_id"),
        "expires_at": tokens.get("expires_at"),
    }

@app.get("/api/mercadolivre/me")
def ml_me(x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    try:
        return get_me()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
