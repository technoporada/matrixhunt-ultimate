# MatrixHunt Ultimate

Lokalna aplikacja webowa. Zbiera oferty darmowych gier ze sklepów,
pokazuje je w przeglądarce, udostępnia proxy stron z sanacją HTML.

## Uruchomienie

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd backend && ../.venv/bin/python main.py
```

Aplikacja wybiera pierwszy wolny port od 8000 i wypisuje go w konsoli.
Nie łączy się z internetem poza sklepami i repozytoriami list filtrów.

## Co faktycznie działa (stan na 2026-10-15, po naprawie merge-markerów)

| | Stan |
|---|---|
| Oferty w bazie | **89**, z 6 źródeł (GamerPower 56, Steam 9, Epic 8, IndieGala 8, Reddit 6, GOG 2) |
| Scrapery aktywne | **6** (GamerPower, Epic, Steam, GOG, IndieGala, Reddit) |
| Scrapery zaparkowane | **8** (zwracały 0 albo timeoutowały) |
| Kolumna `price` | **wszystkie 89 rekordów puste (`''`)** |
| `price_claim` | 70× `'Free'`, 19× `NULL` |
| `price_source` | 70× `listing:*` (gamerpower/indiegala/reddit), 19× `NULL` — **zero `api:*`, czyli zero pomiarów z API sklepu** |
| `price_checked` | ustawione dla 70 wierszy z `price_source` |
| `price_history` | 0 wierszy |
| Stan faktyczny | `price='Free'` nie występuje wcale; potwierdzeniem jest tylko `price_claim='Free'` z `listing:*`, czyli deklaracja strony zbierającej, nie pomiar z API sklepu. |

**Żadna z 89 ofert nie jest potwierdzona pomiarem z API sklepu.**

## Strony

`/` dashboard · `/offers` lista ofert · `/retro` emulator · `/pad` test pada · `/db` podgląd bazy
`/view` proxy stron · `/wiki` · `/bookmarks` · `/flash` · `/uwagi`

## API

44 trasy. Pełna lista: `grep -oE '@app\.(get|post)\("[^"]+"' backend/main.py`

Zmieniające stan wymagają nagłówka `X-MH-Token` z `/api/client-config`.
CORS: `allow_origins=[]`, własne originy przepuszczane ręcznie w `_api_guard`.

## Emulator

`/retro` **nie uruchamia gier.** Mierzy sprzęt w przeglądarce
(WebGL, `hardwareConcurrency`, `deviceMemory`, Gamepad API) i porównuje
z progami z `tools/emulator-db.js` — 26 platform, wymagania CPU/RAM/GPU
i nazwa emulatora, którego użyć.

Ta baza wymagań jest skalowana pod karty dedykowane (RTX/GTX).
Zintegrowane Intel dostają niskie wyniki; na starszym Intel HD
zaledwie część platform przechodzi próg. Skala jest przybliżona,
nie zmierzona dla Twojego sprzętu.
Uczciwe granice skanu (2026-10-15): RAM 0 = przeglądarka ukrywa,
RAM 8 GB = możliwy limit Chromium, Vulkan = UNKNOWN gdy niewykrywalny
(To nie brak), zamaskowany renderer GPU = wynik szacowany.

Aplikacja nie pobiera emulatorów (RetroArch/PCSX2/Dolphin) i nie integruje się z żadnym —
`/retro` to hub linków. Wyjątek: Flash — `/flash` ma wbudowany Ruffle 0.7.1
z `frontend/vendor/ruffle/` (offline, bez CDN, gra w tej samej karcie).

## Baza

SQLite w WAL, tabela `offers`. Sesje i ciasteczka per host w
`~/.local/share/MatrixHunt/`, szyfrowane Fernet.

## Dane w `data/`

| Plik | Co to jest |
|---|---|
| `retro.json` | 9 emulatorów, 5 źródeł ROM, 5 linków `archiveVault` |
| `bookmarks.json` | 1 wpis |
| `seed_offers.json` | pusty (`[]`) |

`archiveVault` to **5 odnośników** do kolekcji na archive.org, nie katalog
gier. Tytuł konkretnej gry w tych paczkach nie jest dostępny przez API.

## Znane ograniczenia (zweryfikowane 2026-10-15)

- `/api/scrapers` zwraca `reason` dla zaparkowanych — naprawione przy usuwaniu merge-markerów (wcześniej `null`)
- dodane `/api/price-changes` (0 wierszy w tej bazie) i liczniki `price_measured / price_claimed / price_unknown` w `/api/stats`
- itch.io zaparkowany: parser stawiał `price="Free"` bez sprawdzenia ceny
- `seed_offers.json` pusty (`[]`) — `load_seed_catalog()` nie dokłada nic
- kolumna `price` pusta dla wszystkich 89 wierszy; klienci muszą czytać `price_claim` / `price_source`
- `.app_settings.json` jawny (`PLAIN:`), gdy vault zablokowany — stan na dziś, plik `backend/.app_settings.json`
- `validate_image` skanuje pierwsze i ostatnie 4096 B
- `vault.unlock()` bez blokady, `write_bytes` nieatomowy
- proxy nieprzetestowane z prawdziwym logowaniem do sklepu
- pad: brak testów na realnym urządzeniu, bo nie było sprzętu w środowisku
- `weryfikuj.sh` przenośny (bez `/home/...`, bez zabijania cudzych procesów, `RUN_DIR=${TMPDIR}/matrixhunt-$USER`); pełny przebieg przekracza 120 s (start serwera = scrape)
- `sync.sh` wymaga celu: `./sync.sh <katalog-docelowy>` albo `MIRROR_DIR=...` — bez twardych ścieżek
- `backend/resolve_delisted_links.py` zepsute niezależnie: `from scrapers.delisted import ...`, a `backend/scrapers/delisted.py` nie istnieje

## Weryfikacja

```bash
.venv/bin/python -m pytest tests/test_ceny.py tests/test_niezmienniki.py -q
# 2026-10-15: 52 passed
```

`./weryfikuj.sh` (pełny, z siecią) nie był puszczany po naprawie — poprzedni historyczny stan z README: **37 z 42 przeszło.**

Historycznie nieudane — proxy zwracało **403 na wszystkich trzech sklepach**:

```
proxy zwraca 200            403
www.gog.com przez proxy     403, 0B
itch.io przez proxy         403, 0B
www.humblebundle.com        403, 0B
```

Wtedy te same sprawdzenia kilka godzin wcześniej przechodziły (GOG 663 kB, itch.io
106 kB, Humble 24 kB). Przyczyna niezbadana. Dopóki nie jest powtórzone po naprawie,
proxy nie jest potwierdzone jako działające.

Stare `test_all.py` leży w `_testy_usuniete/test_all.py.bak`. Aktywne są
`tests/test_ceny.py` + `tests/test_niezmienniki.py` (52 passed 2026-10-15).

---

Wersja 2.0 · Linux Mint 22.3 · Python 3.12
