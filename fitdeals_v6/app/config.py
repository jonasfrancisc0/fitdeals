import os
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: str) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return float(default)


def _int(name: str, default: str) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return int(default)


APP_NAME = os.getenv("APP_NAME", "FitDeals V6").strip()
SITE_ID = os.getenv("SITE_ID", "MLB").strip().upper() or "MLB"

ML_CLIENT_ID = os.getenv("ML_CLIENT_ID", "").strip()
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "").strip()
ML_REDIRECT_URI = os.getenv("ML_REDIRECT_URI", "").strip()
ML_USE_PKCE = _bool("ML_USE_PKCE", "true")

MAX_PRICE = _float("MAX_PRICE", "500")
MIN_DISCOUNT = _float("MIN_DISCOUNT", "10")
REQUIRE_DISCOUNT = _bool("REQUIRE_DISCOUNT", "false")

OFFERS_PER_RUN = max(1, _int("OFFERS_PER_RUN", "20"))
SEARCH_LIMIT_PER_QUERY = min(50, max(1, _int("SEARCH_LIMIT_PER_QUERY", "30")))
PRICE_LOOKUPS_PER_RUN = max(1, _int("PRICE_LOOKUPS_PER_RUN", "50"))
HTTP_TIMEOUT = max(5, _int("HTTP_TIMEOUT", "25"))
INTERVAL_MINUTES = max(5, _int("INTERVAL_MINUTES", "120"))

SEARCH_QUERIES = [
    x.strip() for x in os.getenv(
        "SEARCH_QUERIES",
        "creatina,whey protein,halteres,anilhas,luvas academia,camiseta academia,tenis corrida,mochila academia,garrafa termica,barra proteína,pré treino,corda de pular",
    ).split(",") if x.strip()
]

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "troque-esta-senha")
