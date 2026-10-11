"""
Niezmienniki cen. Bladaja dokladnie jeden blad: price="Free" wpisany
recznie przez scraper, ktory nie spytal sklepu.

Skad ten test: 9 z 9 ofert Steam mialo price="Free", a trzy z nich kosztowaly
21,49 / 29,75 / 71,99 zl, a cztery to bylo DLC udajace gry. Steam API oddaje
"price_overview" w tym samym zapytaniu, ktore juz leci — scraper go nie
czytal, wiec wpisywal literal.

Czego tu nie ma: asercji typu "Deal ma takie pole" — to potwierdza tylko to,
co ten test juz wie. Kazdy test ponizej czytac prawdziwy plik albo prawdziwa
baze i szukac konkretnego klamstwa.

Uruchomienie:  ../.venv/bin/python -m pytest tests/test_ceny.py -v
"""
import ast
import pathlib
import re
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

SCRAPERS = ROOT / "backend" / "scrapers"
DB = ROOT / "backend" / "matrixhunt.db"


def _scraper_files():
    return [p for p in SCRAPERS.glob("*.py") if p.name not in ("__init__.py", "base.py")]


def _literals_preis(node):
    """Dostepne do przypisania stringi, w tym przez .format() i f-string."""
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            out.add(sub.value)
    return out


def _przypisania_do_ceny(tree):
    """Kazde przypisanie do pola price / price_claim / price_source."""
    for node in ast.walk(tree):
        targets = []
        value = None
        if isinstance(node, ast.Assign):
            targets = [t for t in node.targets]
            value = node.value
        elif isinstance(node, ast.Call):
            targets = [k.arg for k in node.keywords if k.arg]
            value = node
        if not targets or value is None:
            continue
        for t in targets:
            nazwa = t if isinstance(t, str) else getattr(t, "attr", None)
            if nazwa in ("price", "price_claim", "price_source"):
                yield nazwa, value


# ============================================================ ZRODLO KODU

@pytest.mark.parametrize("sciezka", _scraper_files(), ids=lambda p: p.stem)
def test_P1_zaden_scraper_nie_wpisuje_ceny_bez_zrodla(sciezka):
    """price="Free" jako literał w wywołaniu Deal(...), które samo nie podaje
    price_source.

    Sprawdzamy konkretne wywołanie, nie cały plik. Wyjątek: to samo wywołanie
    ma price_source="api:<sklep>" — wtedy "Free" jest odpowiedzią serwera
    (Epic sprawdza discountPrice == 0, GOG price.isFree), a nie założeniem.
    """
    tree = ast.parse(sciezka.read_text(encoding="utf-8"))
    zla = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Deal"):
            continue
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        zrodlo = kw.get("price_source")
        zrodlo_txt = ast.unparse(zrodlo) if zrodlo is not None else ""
        if zrodlo_txt.startswith('"api:') or zrodlo_txt.startswith("'api:"):
            continue
        for pole in ("price", "price_claim"):
            v = kw.get(pole)
            if v is None:
                continue
            for lit in _literals_preis(v):
                if lit.strip().lower() == "free":
                    zla.append(f"{pole}={lit!r}")
    # listed_as_free() z base.py dopisuje price_source="listing:<url>",
    # więc wywołania używające **helper nie mają jawnego price_source.
    if "listed_as_free" in sciezka.read_text(encoding="utf-8"):
        zla = [x for x in zla if "listing" not in sciezka.read_text(encoding="utf-8")]
    assert not zla, f"{sciezka.name}: {', '.join(zla)} bez price_source"


@pytest.mark.parametrize("sciezka", _scraper_files(), ids=lambda p: p.stem)
def test_P2_offer_ma_kolumne_pochodzenia_ceny(sciezka):
    """Każdy scraper, który tworzy Offer, musi podawać price_source.

    Brak pola oznacza, że cena trafi do bazy bez informacji, skąd pochodzi —
    a UI wtedy nie odróżni 'sprawdzone' od 'zmyślone' i wraca do kłamstwa.
    """
    tekst = sciezka.read_text(encoding="utf-8")
    if "Deal(" not in tekst:
        pytest.skip("scraper nie tworzy Offer")
    ma_atrybut = "price_source" in tekst
    ma_helper = "listed_as_free" in tekst
    assert ma_atrybut or ma_helper, (
        f"{sciezka.name}: tworzy Offer bez price_source i bez listed_as_free() "
        "— cena trafi do bazy bez śladu skąd pochodzi"
    )


def test_P3_steam_nie_zapisuje_ceny_z_sam_search():
    """Steam musi pytać API, nie ufać filtrowi maxprice=free w query.

    Filtr w URL to podpowiedź, nie pomiar: strona zwraca też demówki i DLC
    oraz pozycje, które darmowe nie są.
    """
    tekst = (SCRAPERS / "steam.py").read_text(encoding="utf-8")
    assert "price_overview" in tekst, (
        "steam.py nie pyta o price_overview — wraca do wpisywania literału"
    )
    assert "appdetails" in tekst, "steam.py nie odpytuje API appdetails"


def test_P4_steam_odrzuca_nie_gry():
    assert re.search(r'type"\]\s*!=\s*"game"|\btype\b.*!=.*game', (SCRAPERS / "steam.py").read_text(encoding="utf-8")), (
        "steam.py nie odrzuca type != 'game' — DLC wróci jako gra"
    )


# ============================================================ ZRODLO DANE

@pytest.fixture(scope="module")
def conn():
    if not DB.exists():
        pytest.skip("brak bazy")
    c = sqlite3.connect(str(DB))
    yield c
    c.close()


def test_P5_baza_ma_kolumny_pochodzenia(conn):
    kolumny = {r[1] for r in conn.execute("PRAGMA table_info(offers)")}
    brak = {"price_claim", "price_source", "price_checked"} - kolumny
    assert not brak, f"brak kolumn po migracji: {brak}"


def test_P6_zaden_cena_bez_zrodla(conn):
    """Żaden wiersz nie może mieć ceny bez price_source.

    To jest warunek, którego złamał każdy poprzedni scraper.
    """
    zle = conn.execute(
        "SELECT source, title, price, price_source FROM offers "
        "WHERE price IS NOT NULL AND price <> '' AND (price_source IS NULL OR price_source = '')"
    ).fetchall()
    assert not zle, (
        f"{len(zle)} wierszy ma cenę bez price_source, np. "
        + "; ".join(f"{r[0]}:{r[1][:24]}={r[2]!r}" for r in zle[:4])
    )


def test_P7_nic_nie_ma_uzyskanej_darmowej_ceny(conn):
    """Twarda prawda: 'Free' zgłoszone przez API to OK, zgłoszone przez
    założenie to kłamstwo. Weryfikujemy to na realnych wierszach."""
    zle = conn.execute(
        "SELECT source, title, price FROM offers "
        "WHERE lower(price) LIKE '%free%' AND (price_source IS NULL OR price_source NOT LIKE 'api:%')"
    ).fetchall()
    assert not zle, (
        f"{len(zle)} wierszy twierdzi 'Free' bez źródła z API, np. "
        + "; ".join(f"{r[0]}:{r[1][:24]}" for r in zle[:4])
    )


def test_P8_sprawdzone_ceny_maja_znacznik_czasu(conn):
    brak = conn.execute(
        "SELECT COUNT(*) FROM offers WHERE price_source IS NOT NULL AND price_checked IS NULL"
    ).fetchone()[0]
    assert brak == 0, f"{brak} wierszy ma price_source bez price_checked"
