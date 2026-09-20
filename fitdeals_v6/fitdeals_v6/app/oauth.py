import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

import requests

from . import db
from .config import HTTP_TIMEOUT, ML_CLIENT_ID, ML_CLIENT_SECRET, ML_REDIRECT_URI, ML_USE_PKCE

AUTH = "https://auth.mercadolivre.com.br/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def build_url() -> str:
    if not all([ML_CLIENT_ID, ML_CLIENT_SECRET, ML_REDIRECT_URI]):
        raise RuntimeError("Configure ML_CLIENT_ID, ML_CLIENT_SECRET e ML_REDIRECT_URI.")

    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64) if ML_USE_PKCE else None
    params = {
        "response_type": "code",
        "client_id": ML_CLIENT_ID,
        "redirect_uri": ML_REDIRECT_URI,
        "state": state,
    }
    if verifier:
        params.update(code_challenge=_pkce_challenge(verifier), code_challenge_method="S256")
    db.save_state(state, verifier)
    return AUTH + "?" + urlencode(params)


def exchange(code: str, state: str) -> dict:
    stored = db.pop_state(state)
    if not stored:
        raise RuntimeError("State OAuth inválido. Clique em Conectar Mercado Livre novamente.")

    data = {
        "grant_type": "authorization_code",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "code": code,
        "redirect_uri": ML_REDIRECT_URI,
    }
    if ML_USE_PKCE:
        data["code_verifier"] = stored.get("code_verifier") or ""

    r = requests.post(TOKEN_URL, data=data, timeout=HTTP_TIMEOUT)
    if not r.ok:
        raise RuntimeError(f"OAuth HTTP {r.status_code}: {r.text[:600]}")
    payload = r.json()
    db.save_tokens(
        payload["access_token"],
        payload.get("refresh_token"),
        str(payload.get("user_id", "")),
        int(time.time()) + int(payload.get("expires_in", 21600)),
    )
    return payload


def token() -> str | None:
    stored = db.tokens()
    if not stored:
        return None

    expires_at = int(stored.get("expires_at") or 0)
    if expires_at > int(time.time()) + 120 and stored.get("access_token"):
        return str(stored["access_token"])

    refresh = stored.get("refresh_token")
    if not refresh:
        return None

    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": ML_CLIENT_ID,
            "client_secret": ML_CLIENT_SECRET,
            "refresh_token": refresh,
        },
        timeout=HTTP_TIMEOUT,
    )
    if not r.ok:
        raise RuntimeError(f"Refresh HTTP {r.status_code}: {r.text[:600]}")

    payload = r.json()
    db.save_tokens(
        payload["access_token"],
        payload.get("refresh_token") or refresh,
        str(payload.get("user_id", stored.get("user_id", ""))),
        int(time.time()) + int(payload.get("expires_in", 21600)),
    )
    return str(payload["access_token"])
