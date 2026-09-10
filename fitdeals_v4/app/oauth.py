import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

import requests

from . import db
from .config import ML_CLIENT_ID, ML_CLIENT_SECRET, ML_REDIRECT_URI, ML_USE_PKCE

AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"

def _pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge

def build_authorization_url():
    if not ML_CLIENT_ID or not ML_REDIRECT_URI:
        raise RuntimeError("Configure ML_CLIENT_ID e ML_REDIRECT_URI no .env")

    state = secrets.token_urlsafe(32)
    verifier = None
    params = {
        "response_type": "code",
        "client_id": ML_CLIENT_ID,
        "redirect_uri": ML_REDIRECT_URI,
        "state": state,
    }

    if ML_USE_PKCE:
        verifier, challenge = _pkce_pair()
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"

    db.save_oauth_state(state, verifier)
    return AUTH_URL + "?" + urlencode(params)

def exchange_code(code, state):
    saved = db.pop_oauth_state(state)
    if not saved:
        raise RuntimeError("State OAuth inválido ou expirado. Tente conectar novamente.")

    data = {
        "grant_type": "authorization_code",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "code": code,
        "redirect_uri": ML_REDIRECT_URI,
    }

    if ML_USE_PKCE:
        data["code_verifier"] = saved.get("code_verifier")

    response = requests.post(TOKEN_URL, data=data, timeout=30)
    response.raise_for_status()
    payload = response.json()

    expires_in = int(payload.get("expires_in", 21600))
    expires_at = int(time.time()) + expires_in
    db.save_tokens(
        payload["access_token"],
        payload.get("refresh_token"),
        str(payload.get("user_id", "")),
        expires_at
    )
    return payload

def refresh_access_token():
    tokens = db.get_tokens()
    if not tokens or not tokens.get("refresh_token"):
        return None

    data = {
        "grant_type": "refresh_token",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "refresh_token": tokens["refresh_token"],
    }
    response = requests.post(TOKEN_URL, data=data, timeout=30)
    response.raise_for_status()
    payload = response.json()

    expires_in = int(payload.get("expires_in", 21600))
    expires_at = int(time.time()) + expires_in
    db.save_tokens(
        payload["access_token"],
        payload.get("refresh_token"),
        str(payload.get("user_id", tokens.get("user_id", ""))),
        expires_at
    )
    return payload

def get_valid_access_token():
    tokens = db.get_tokens()
    if not tokens:
        return None

    if tokens.get("expires_at", 0) > int(time.time()) + 120:
        return tokens["access_token"]

    refreshed = refresh_access_token()
    return refreshed["access_token"] if refreshed else None
