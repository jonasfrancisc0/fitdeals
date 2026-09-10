import threading
import time

from .config import INTERVAL_MINUTES
from .db import init_db, save_offer
from .mercadolivre import collect_offers

_started = False

def collect_once():
    offers = collect_offers()
    for offer in offers:
        save_offer(offer)
    return len(offers)

def _loop():
    while True:
        try:
            collect_once()
        except Exception as exc:
            print(f"[FitDeals] coleta automática: {exc}")
        time.sleep(max(1, INTERVAL_MINUTES) * 60)

def start_scheduler():
    global _started
    if _started:
        return
    _started = True
    init_db()
    thread = threading.Thread(target=_loop, daemon=True, name="fitdeals-scheduler")
    thread.start()
