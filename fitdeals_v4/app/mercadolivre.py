import requests

from .config import MAX_PRICE, MIN_DISCOUNT, OFFERS_PER_RUN, SEARCH_QUERIES
from .oauth import get_valid_access_token

API = "https://api.mercadolibre.com"
SITE = "MLB"

def _get(path, params=None, authenticated=False):
    headers = {}
    if authenticated:
        token = get_valid_access_token()
        if not token:
            raise RuntimeError("Mercado Livre não está conectado. Clique em 'Conectar Mercado Livre'.")
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(API + path, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

def get_me():
    return _get("/users/me", authenticated=True)

def get_item_price(item_id):
    try:
        payload = _get(f"/items/{item_id}/prices", authenticated=False)
        prices = payload.get("prices", [])
        valid = [p for p in prices if p.get("amount") is not None]
        if not valid:
            return None, None
        promotions = [p for p in valid if p.get("type") == "promotion"]
        chosen = promotions[0] if promotions else valid[0]
        standard = next((p for p in valid if p.get("type") == "standard"), None)
        current = float(chosen["amount"])
        original = float(standard["amount"]) if standard else None
        return current, original
    except requests.HTTPError:
        return None, None

def search_query(query, limit=20):
    payload = _get(f"/sites/{SITE}/search", params={"q": query, "limit": limit})
    return payload.get("results", [])

def normalize_item(item):
    item_id = item.get("id")
    current, original = get_item_price(item_id)

    if current is None:
        current = item.get("price")
    if original is None:
        original = item.get("original_price")

    try:
        current_f = float(current) if current is not None else None
    except (TypeError, ValueError):
        current_f = None

    try:
        original_f = float(original) if original is not None else None
    except (TypeError, ValueError):
        original_f = None

    discount = None
    if current_f is not None and original_f and original_f > current_f:
        discount = round((1 - current_f / original_f) * 100, 1)

    return {
        "item_id": item_id,
        "title": item.get("title", ""),
        "price": current_f,
        "original_price": original_f,
        "discount": discount or 0,
        "permalink": item.get("permalink", ""),
        # O FitDeals não inventa parâmetros de afiliado.
        # Esta URL pode ser substituída por uma URL oficial do seu programa de afiliados.
        "affiliate_url": "",
        "thumbnail": item.get("thumbnail", ""),
        "source_json": item,
    }

def collect_offers():
    seen = set()
    results = []

    for query in SEARCH_QUERIES:
        try:
            items = search_query(query, limit=max(10, OFFERS_PER_RUN))
        except Exception:
            continue

        for item in items:
            item_id = item.get("id")
            if not item_id or item_id in seen:
                continue
            seen.add(item_id)

            offer = normalize_item(item)
            price = offer["price"]
            discount = offer["discount"]

            if price is None or price > MAX_PRICE:
                continue
            if discount < MIN_DISCOUNT:
                continue

            results.append(offer)

            if len(results) >= OFFERS_PER_RUN:
                return results

    results.sort(key=lambda x: (x.get("discount") or 0), reverse=True)
    return results[:OFFERS_PER_RUN]
