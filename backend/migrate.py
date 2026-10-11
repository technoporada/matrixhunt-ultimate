"""One-off schema migration. create_all() does NOT add columns to a table that
already exists — it creates missing tables and ignores existing ones — so
adding price_claim silently did nothing until a scraper wrote to a column that
was never there. This runs the ALTER TABLEs by hand and is safe to re-run.

Usage:  python3 migrate.py [ścieżka/do/bazy.db]
"""
import sqlite3
import sys
from pathlib import Path

COLUMNS = [
    ("price_claim", "TEXT"),
    ("price_source", "TEXT"),
    ("price_checked", "TIMESTAMP"),
]

PRICE_HISTORY = """
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id INTEGER NOT NULL,
    price_claim TEXT,
    price_source TEXT,
    seen_at TIMESTAMP
)
"""

INDEX = "CREATE INDEX IF NOT EXISTS ix_price_history_offer_day ON price_history (offer_id, seen_at)"


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    path = Path(argv[0]) if argv else Path(__file__).parent / "matrixhunt.db"
    if not path.exists():
        print(f"Brak bazy: {path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(path))
    try:
        tabela = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='offers'"
        ).fetchone()
        if not tabela:
            print(f"{path} nie ma tabeli offers — nic do migracji.", file=sys.stderr)
            return 1

        istniejace = {r[1] for r in conn.execute("PRAGMA table_info(offers)")}
        dodane = []
        for nazwa, typ in COLUMNS:
            if nazwa in istniejace:
                print(f"  = {nazwa} już jest")
                continue
            conn.execute(f"ALTER TABLE offers ADD COLUMN {nazwa} {typ}")
            dodane.append(nazwa)
            print(f"  + {nazwa} {typ}")

        conn.execute(PRICE_HISTORY)
        conn.execute(INDEX)
        conn.commit()

        print()
        print(f"Dodano kolumn: {', '.join(dodane) if dodane else 'brak — baza już zaktualizowana'}")
        print("Tabela price_history: gotowa")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
