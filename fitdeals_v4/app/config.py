import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "FitDeals V4")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fitdeals.db")

ML_CLIENT_ID = os.getenv("ML_CLIENT_ID", "").strip()
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "").strip()
ML_REDIRECT_URI = os.getenv("ML_REDIRECT_URI", "").strip()
ML_USE_PKCE = os.getenv("ML_USE_PKCE", "true").lower() in {"1", "true", "yes", "on"}

MAX_PRICE = float(os.getenv("MAX_PRICE", "500"))
MIN_DISCOUNT = float(os.getenv("MIN_DISCOUNT", "20"))
OFFERS_PER_RUN = int(os.getenv("OFFERS_PER_RUN", "10"))
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "120"))
SEARCH_QUERIES = [x.strip() for x in os.getenv(
    "SEARCH_QUERIES",
    "halteres,creatina,whey protein,tênis de corrida,camiseta academia"
).split(",") if x.strip()]

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "troque-esta-senha")
