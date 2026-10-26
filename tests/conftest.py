"""Wspólne fixture'y dla testów MatrixHunt Ultimate."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

DB = ROOT / "backend" / "matrixhunt.db"


def _seed_if_empty():
    """Zasiej bazę z data/seed_offers.json, jeśli jest pusta/nie istnieje.
    Dzięki temu testy są samowystarczalne (CI, świeży klon) bez scrape'u sieci."""
    try:
        if not DB.exists() or DB.stat().st_size == 0:
            import main as _main
            _main.load_seed_catalog()
    except Exception:
        pass


def pytest_sessionstart(session):
    _seed_if_empty()