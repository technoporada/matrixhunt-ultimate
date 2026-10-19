"""
Testy niezmiennikow. Sprawdzaja tylko to, co da sie sprawdzic w obiekcie:
prawdziwe pliki list, prawdziwa baza, prawdziwy serwer.

Czego tu nie ma i dlaczego:
  - asercji "zwraca to, co zwraca" (test pisany przez tego samego model,
    ktory napisal kod, nie ma wartosci dowodowej),
  - testow na zewnetrznych sklepach bez sieci (daja zielone bez danych).

Testy dzielace sposob weryfikacji z moimi wczesniejszymi:
  F1-F4  niezmienniki na prawdziwych plikach list filtrów,
  D1-D5  niezmienniki na prawdziwej bazie SQLite,
  S1-S6  niezmienniki na zyjacym serwerze (token, CORS, SSRF, /data),
  T1-T3  F2P/DLC na prawdziwych tytulach i opisach.

Uruchomienie:  ../.venv/bin/python -m pytest tests/ -v
Serwer musi dzialac. Testy S* pomijaja sie, jesli go nie ma.
"""
import json
import os
import re
import pathlib
import sqlite3
import subprocess
import sys
import time

import pytest
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

DB = ROOT / "backend" / "matrixhunt.db"
LISTS = ROOT / "backend" / "filterlists.py"


def _run_dir():
    import os
    import tempfile
    env = os.environ.get("MH_RUN_DIR", "").strip()
    if env:
        return pathlib.Path(env)
    user = os.environ.get("USER", "u") or "u"
    return pathlib.Path(os.environ.get("TMPDIR") or tempfile.gettempdir()) / f"matrixhunt-{user}"


def _port():
    """Port z env / pliku startowego, inaczej z aktywnych listenerow."""
    env = os.environ.get("MH_PORT", "").strip()
    if env.isdigit():
        return int(env)
    for log in (_run_dir() / "port.txt",
                ROOT / ".tmp" / "port.txt"):
        try:
            if log.exists():
                txt = log.read_text().strip()
                if txt.isdigit():
                    return int(txt)
        except OSError:
            pass
    import socket
    for p in range(8000, 8020):
        s = socket.socket()
        try:
            s.connect(("127.0.0.1", p))
            s.close()
            return p
        except OSError:
            s.close()
    return None


PORT = _port()
BASE = f"http://127.0.0.1:{PORT}" if PORT else None
needs_server = pytest.mark.skipif(not BASE, reason="serwer nie dziala")


def get(path, headers=None, timeout=30):
    req = urllib.request.Request(BASE + path, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)


# ================================================================ FILTRY
@pytest.fixture(scope="module")
def engine():
    from filterlists import get_engine
    return get_engine()


def _rules_engines():
    """Reguly jako liste surowych wzorcow, zrodlo prawdy z pliku."""
    src = LISTS.read_text()
    return src


def test_F1_zaden_zawezony_regex_nie_blokuje_calego_hosta(engine):
    """Najczestszy blad w tym projekcie: regula '/ads' blokujaca caly host.
    Przechodzi po wszystkich regulach z prawdziwych plikow list."""
    reguly = [r for r in engine.regex_rules if not r.allow]
    assert len(reguly) > 1000, f"tylko {len(reguly)} regul - test by nic nie sprawdzil"
    zle = []
    for r in reguly:
        # regula ktora ma wlasny host nie moze blokowac innych
        if r.domain:
            continue
        wz = r.raw
        host = wz.split("/")[0].split("$")[0].strip().lower()
        # patrzymy tylko na regule, ktore moga chwycic caly host
        if host.startswith(("&", "-", "|", "?", "=", "~", ".")):
            continue
        if "." not in host or "/" in host or "*" in host:
            continue
        if re.fullmatch(r"[a-z0-9.-]+", host):
            zablokowane, reg = engine.check("https://neutral.example/",
                                            f"https://{host}/", "script")
            if zablokowane:
                zle.append(f"{wz} -> {reg}")
    assert not zle, f"{len(zle)} regul blokujacych caly host, np. {zle[:5]}"


def test_F2_trackery_sa_blokowane(engine):
    for h in ("doubleclick.net", "googlesyndication.com", "scorecardresearch.com",
              "hotjar.com"):
        zablokowane, reg = engine.check("https://neutral.example/",
                                       f"https://{h}/p.gif", "image")
        assert zablokowane, f"tracker przepuszczony: {h}"


def test_F3_zdrowe_hosty_przepuszczone(engine):
    for h in ("gog.com", "www.itch.io", "store.epicgames.com",
              "www.humblebundle.com", "cdn.jsdelivr.net", "fonts.googleapis.com"):
        zablokowane, reg = engine.check("https://neutral.example/",
                                       f"https://{h}/app.js", "script")
        assert not zablokowane, \
            f"zdrowy host zablokowany: {h} ({reg})"


def test_F4_silnik_jest_buforowany(engine):
    """get_engine() ma cache - 1000 wywolan bez czekania na I/O."""
    from filterlists import get_engine
    t0 = time.perf_counter()
    for _ in range(1000):
        get_engine()
    assert time.perf_counter() - t0 < 2.0, "brak cache - kazde wywolanie czyta pliki"


# ================================================================ BAZA
@pytest.fixture(scope="module")
def conn():
    if not DB.exists():
        pytest.skip("brak bazy")
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    yield c
    c.close()


def test_D1_baza_niepusta(conn):
    n = conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
    assert n > 0, "baza pusta"


def test_D2_zero_f2p(conn):
    """F2P ma byc wyrzucone na wejsciu, wiec baza nie moze go zawierac.
    Sprawdzam tu tresc, nie tylko tytul - opisy wylapuja to, czego
    sam tytul nie pokazuje."""
    from scrapers.base import is_f2p_or_addon
    zle = []
    for t, d, s in conn.execute("SELECT title, description, source FROM offers"):
        if is_f2p_or_addon(t or "") or is_f2p_or_addon(d or ""):
            zle.append(f"{s}: {t}")
    assert not zle, f"F2P/DLC w bazie: {zle[:8]}"


def test_D3_zero_prefiksow_sklepow(conn):
    """Tytul typu '[Steam] (Game)' to smiec z katalogu zapasowego."""
    zle = [t for (t,) in conn.execute(
        "SELECT title FROM offers")
        if t and t.strip().startswith(("[", "("))]
    assert not zle, f"prefiksy w tytulach: {zle[:8]}"


def test_D4_tylko_http_i_https(conn):
    zle = [u for (u,) in conn.execute("SELECT url FROM offers")
           if u and not u.startswith(("http://", "https://"))]
    assert not zle, f"zle schematy URL: {zle[:5]}"


def test_D5_zero_wykonywalnych(conn):
    zle = [u for (u,) in conn.execute("SELECT url FROM offers")
           if u and u.lower().endswith((".exe", ".msi", ".bat", ".sh", ".scr"))]
    assert not zle, f"linki do wykonywalnych: {zle[:5]}"


# ================================================================ SERWER
@needs_server
def test_S1_wszystkie_trasy_zyja():
    for r in ("/", "/retro", "/pad", "/db", "/view", "/wiki",
              "/bookmarks", "/flash"):
        c, _, _ = get(r)
        assert c == 200, f"{r} -> {c}"


@needs_server
def test_S2_post_bez_tokenu_403():
    req = urllib.request.Request(BASE + "/api/scrape", data=b"{}", method="POST")
    try:
        urllib.request.urlopen(req, timeout=10)
        raise AssertionError("POST bez tokenu przeszedl")
    except urllib.error.HTTPError as e:
        assert e.code == 403, f"oczekiwano 403, jest {e.code}"


@needs_server
def test_S3_obcy_origin_ma_brak_cors():
    for origin in ("http://evil.com", "http://localhost:9999"):
        _, _, h = get("/api/stats", headers={"Origin": origin})
        assert not h.get("Access-Control-Allow-Origin"), \
            f"obcy origin {origin} dostał CORS"


@needs_server
def test_S4_ssrf_zablokowane():
    cele = ["http://127.0.0.1:%d/api/stats" % PORT,
            "http://169.254.169.254/latest/meta-data/",
            "file:///etc/passwd",
            "http://localhost:%d/" % PORT]
    for u in cele:
        q = urllib.parse.quote(u, safe="")
        c, body, _ = get(f"/api/clean?url={q}")
        assert c == 403, f"SSRF przepuszczone: {u} -> {c} {body[:80]}"


@needs_server
def test_S5_dane_audytu_nie_sa_publiczne():
    c, _, _ = get("/data/vulncheck.json")
    assert c == 404, f"audyt wystawiony publicznie: {c}"
    c, _, _ = get("/data/../../../etc/passwd")
    assert c == 404, f"traversal przeszedl: {c}"
    c, _, _ = get("/data/seed_offers.json")
    assert c == 200, "katalog zapasowy powinien byc dostepny"


@needs_server
def test_S6_limit_jest_przycinany():
    c, body, _ = get("/api/offers?limit=1000000000")
    assert c == 200
    dane = json.loads(body)
    assert len(dane) <= 1000, f"limit nie przyciety: {len(dane)}"


# ================================================================ F2P / DLC
PRAWZIWE = [
    "Hollow Knight", "Celeste", "Stardew Valley", "Terraria",
    "Dead Cells", "Hades", "Shovel Knight", "Night in the Woods",
    "Undertale", "Fez", "Outlast", "Hotline Miami", "A Short Hike",
    "Gris", "Outer Wilds", "Katana Zero", "Slay the Spire",
    "Disco Elysium", "Balatro", "Dave the Diver", "Hades II",
]
F2P_I_DLC = [
    "Apex Legends", "Fortnite", "Call of Duty: Warzone", "PUBG: BATTLEGROUNDS",
    "Genshin Impact", "Valorant", "League of Legends",
    "Dying Light: The Beast - DLC", "Cyberpunk 2077: Phantom Liberty",
    "Elden Ring: Shadow of the Erdtree", "Resident Evil 4: Separate Ways",
    "Destiny 2", "Rocket League", "Warframe", "Path of Exile",
    "Overwatch 2", "Dying Light 2 Stay Human Expansion",
]


def test_T1_prawdziwe_gry_przechodza():
    from scrapers.base import is_f2p_or_addon
    zle = [t for t in PRAWZIWE if is_f2p_or_addon(t)]
    assert not zle, f"odrzucone prawdziwe gry: {zle}"


def test_T2_f2p_jest_odrzucane():
    from scrapers.base import is_f2p_or_addon
    przepuszczone = [t for t in F2P_I_DLC if not is_f2p_or_addon(t)]
    assert not przepuszczone, f"F2P/DLC przepuszczone: {przepuszczone}"


def test_T3_f2p_w_opisie():
    """Tytul moze byc czysty - 'Shadow of the Erdtree' bez prefiksu DLC.
    Dopisek w opisie musi zostac zlapany."""
    from scrapers.base import is_f2p_or_addon
    opisy = [
        "Free to play this week. Download now and keep it forever.",
        "This DLC requires the base game. Free-to-play weekend.",
        "Free to play multiplayer mode, no purchase required.",
    ]
    przepuszczone = [o for o in opisy if not is_f2p_or_addon(o)]
    assert not przepuszczone, f"opis F2P przepuszczony: {przepuszczone}"
