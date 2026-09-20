from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import (
    HTTP_TIMEOUT,
    MAX_PRICE,
    MIN_DISCOUNT,
    OFFERS_PER_RUN,
    PRICE_LOOKUPS_PER_RUN,
    REQUIRE_DISCOUNT,
    SEARCH_LIMIT_PER_QUERY,
    SEARCH_QUERIES,
    SITE_ID,
)
from .oauth import token

API = "https://api.mercadolibre.com"


class MercadoLivreClient:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.price_calls = 0
        self.search_candidates = 0
        self.unique_candidates = 0
        self.per_query: list[dict[str, Any]] = []
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=2,
            read=2,
            status=3,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None, auth: bool = False) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "FitDeals/6.0",
        }
        if auth:
            access = token()
            if not access:
                raise RuntimeError("Mercado Livre não conectado. Conecte o Mercado Livre novamente.")
            headers["Authorization"] = f"Bearer {access}"

        url = API + path
        response = self.session.request(method, url, params=params, headers=headers, timeout=HTTP_TIMEOUT)
        if not response.ok:
            detail = response.text[:600].replace("\n", " ")
            raise RuntimeError(f"HTTP {response.status_code} em {path}: {detail}")
        if not response.content:
            return {}
        return response.json()

    def verify_connection(self) -> dict[str, Any]:
        access = token()
        if not access:
            return {"connected": False, "reason": "Sem access token armazenado."}
        try:
            me = self._request("GET", "/users/me", auth=True)
            return {
                "connected": True,
                "user_id": me.get("id"),
                "nickname": me.get("nickname"),
                "site_id": me.get("site_id"),
            }
        except Exception as exc:
            return {"connected": False, "reason": str(exc)}

    def search(self, query: str) -> list[dict[str, Any]]:
        payload = self._request(
            "GET",
            f"/sites/{SITE_ID}/search",
            params={
                "q": query,
                "limit": SEARCH_LIMIT_PER_QUERY,
                "offset": 0,
            },
            auth=False,
        )
        return payload.get("results") or []

    @staticmethod
    def _num(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _sale_price(self, item_id: str) -> tuple[float | None, float | None, str, dict[str, Any]]:
        self.price_calls += 1
        payload = self._request(
            "GET",
            f"/items/{item_id}/sale_price",
            params={"context": "channel_marketplace"},
            auth=True,
        )
        current = self._num(payload.get("amount"))
        original = self._num(payload.get("regular_amount"))
        promotion = bool(payload.get("metadata", {}).get("promotion_id"))
        return current, original, "promotion" if promotion or (original is not None and current is not None and original > current) else "standard", payload

    def _prices(self, item_id: str) -> tuple[float | None, float | None, str, dict[str, Any]]:
        self.price_calls += 1
        payload = self._request("GET", f"/items/{item_id}/prices", auth=True)
        prices = payload.get("prices") or []
        valid = []
        for p in prices:
            amount = self._num(p.get("amount"))
            if amount is None:
                continue
            restrictions = (p.get("conditions") or {}).get("context_restrictions") or []
            # We want the marketplace price whenever it is explicitly available.
            priority = 0 if "channel_marketplace" in restrictions or not restrictions else 1
            valid.append((priority, p))
        valid.sort(key=lambda x: (x[0], -(self._num(x[1].get("amount")) or 0)))
        promotions = [p for _, p in valid if p.get("type") == "promotion"]
        if promotions:
            p = promotions[0]
            return self._num(p.get("amount")), self._num(p.get("regular_amount")), "promotion", p
        standards = [p for _, p in valid if p.get("type") == "standard"]
        if standards:
            p = standards[0]
            return self._num(p.get("amount")), self._num(p.get("regular_amount")), "standard", p
        return None, None, "unknown", {}

    def price_for_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        item_id = str(item.get("id") or "")
        if not item_id:
            return None

        current: float | None = None
        original: float | None = None
        price_type = "fallback"
        price_source = "search"
        price_raw: dict[str, Any] = {}

        try:
            current, original, price_type, price_raw = self._sale_price(item_id)
            price_source = "sale_price"
        except Exception as sale_exc:
            self.errors.append(f"{item_id}: sale_price falhou; tentando /prices -> {sale_exc}")
            try:
                current, original, price_type, price_raw = self._prices(item_id)
                price_source = "prices"
            except Exception as prices_exc:
                self.errors.append(f"{item_id}: /prices falhou; usando busca -> {prices_exc}")

        if current is None:
            current = self._num(item.get("price"))
            if current is not None:
                price_source = "search.price"
        if original is None:
            original = self._num(item.get("original_price"))

        if current is None:
            self.errors.append(f"{item_id}: não foi possível obter um preço.")
            return None

        discount = 0.0
        if original is not None and original > current:
            discount = round((1 - current / original) * 100, 1)

        return {
            "item_id": item_id,
            "title": item.get("title") or "Sem título",
            "price": current,
            "original_price": original,
            "discount": discount,
            "score": round(discount + (12 if price_type == "promotion" else 0), 2),
            "price_type": price_type,
            "price_source": price_source,
            "promotion_detected": price_type == "promotion" or discount > 0,
            "permalink": item.get("permalink") or "",
            "affiliate_url": "",
            "thumbnail": item.get("thumbnail") or "",
            "source_json": {
                "search_item": item,
                "price_response": price_raw,
                "collected_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def collect(self) -> list[dict[str, Any]]:
        seen: set[str] = set()
        candidates: list[dict[str, Any]] = []

        for query in SEARCH_QUERIES:
            try:
                results = self.search(query)
                self.search_candidates += len(results)
                added = 0
                for item in results:
                    item_id = str(item.get("id") or "")
                    if item_id and item_id not in seen:
                        seen.add(item_id)
                        candidates.append(item)
                        added += 1
                self.per_query.append({"query": query, "results": len(results), "new_unique": added})
            except Exception as exc:
                self.per_query.append({"query": query, "results": 0, "new_unique": 0, "error": str(exc)})
                self.errors.append(f"Busca '{query}': {exc}")

        self.unique_candidates = len(candidates)
        offers: list[dict[str, Any]] = []

        # Do price lookups only for a bounded number of candidates to respect rate limits.
        for item in candidates[:PRICE_LOOKUPS_PER_RUN]:
            offer = self.price_for_item(item)
            if not offer:
                continue
            if offer["price"] > MAX_PRICE:
                continue
            if REQUIRE_DISCOUNT and offer["discount"] < MIN_DISCOUNT:
                continue
            if not REQUIRE_DISCOUNT and offer["discount"] < MIN_DISCOUNT:
                # A minimum configured discount is still respected; set MIN_DISCOUNT=0 to show all.
                continue
            offers.append(offer)

        offers.sort(key=lambda x: (x["score"], x["discount"], -x["price"]), reverse=True)
        return offers[:OFFERS_PER_RUN]

    def diagnostics(self) -> dict[str, Any]:
        return {
            "search_candidates": self.search_candidates,
            "unique_candidates": self.unique_candidates,
            "price_calls": self.price_calls,
            "offers_found": 0,
            "queries": self.per_query,
            "errors": self.errors[:50],
        }


# Backwards-compatible alias used by older imports.
Client = MercadoLivreClient
