# MatrixHunt Ultimate

Lokalna aplikacja webowa. Zbiera oferty darmowych gier ze sklepów,
pokazuje je w przeglądarce, udostępnia proxy stron z sanacją HTML.
Zero zapytań do obcych CDN — React, Babel i Ruffle są zvendorowane lokalnie.

## Uruchomienie

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd backend && ../.venv/bin/python main.py
```

Aplikacja wybiera pierwszy wolny port od 8000 i wypisuje go w konsoli.
Nie łączy się z internetem poza sklepami i repozytoriami list filtrów.

## Strony

| Adres | Plik | Co to jest |
|---|---|---|
| `/` | `frontend/index.html` | dashboard ofert |
| `/offers` | `frontend/offers.html` | lista ofert (osobny widok) |
| `/view` | `tools/viewer.html` | proxy stron z sanacją HTML |
| `/db` | `tools/db.html` | podgląd bazy |
| `/retro` | `tools/retro.html` | hub: emulatory, ROM, vault, delisted, flash, skan sprzętu |
| `/pad` | `frontend/pad_test.html` | test pada (Gamepad API) |
| `/wiki` | `tools/wiki.html` | wiki |
| `/bookmarks` | `tools/bookmarks.html` | zakładki |
| `/flash` | `tools/flash_player.html` | player Flash (Ruffle 0.7.1, lokalnie, ta sama karta) |
| `/uwagi` | `tools/uwagi.html` | uwagi |

Górne menu z 10 linkami jest na `/` i na `/offers` — nic nie jest schowane w stopce.

## API

44 trasy. Pełna lista: `grep -oE '@app\.(get|post)\("[^"]+"' backend/main.py`

Zmieniające stan wymagają nagłówka `X-MH-Token` z `/api/client-config`.
CORS: `allow_origins=[]`, własne originy przepuszczane ręcznie w `_api_guard`.
Treści 18+: `/api/offers` defaultowo je pomija, `?nsfw=1` tylko po bramce wieku
w UI (modal 18+); RSS nigdy nie niesie 18+.

## Scrapery i ceny

- Aktywne (7): GamerPower, Epic, Steam, GOG, IndieGala, Reddit,
  Łowcy Gier (polskie `lowcygier.pl/darmowe/` przez RSS — Cloudflare blokuje stronę).
- Zaparkowane (8): FreeSteamKeys, Nebula, SharewareOnSale, Humble, GameJolt,
  GiveawayRadar, FreeToGame, Itch.io. Powód każdego widać w `/api/scrapers` (`reason`).
- Polityka cen: `price` bywa puste; wiążące są `price_claim` + `price_source`.
  `api:<sklep>` = pomiar z API sklepu, `listing:<url>` = deklaracja strony
  zbierającej. Wiersz bez `price_source` to cena niesprawdzona.

Migawka lokalnej bazy z 2026-10-15 (baza jest lokalna, nie w repo):
89 ofert (GamerPower 56, Steam 9, Epic 8, IndieGala 8, Reddit 6, GOG 2),
`price_claim='Free'` dla 70, 19× NULL, **zero `api:*`** — czyli na ten dzień
żadna oferta nie była potwierdzona pomiarem z API sklepu. `price_history`: 0 wierszy.

## Emulator i Flash

`/retro` **nie uruchamia gier** (poza Flash — niżej). Mierzy sprzęt w przeglądarce
(WebGL, `hardwareConcurrency`, `deviceMemory`, Gamepad API) i porównuje
z progami z `tools/emulator-db.js` — 26 platform, wymagania CPU/RAM/GPU
i nazwa emulatora, którego użyć.

Uczciwe granice skanu: RAM 0 = przeglądarka ukrywa (Firefox/Safari),
RAM 8 GB = możliwy limit Chromium (możesz mieć więcej),
Vulkan = UNKNOWN gdy niewykrywalny (to nie to samo co brak),
zamaskowany renderer GPU = wynik szacowany, nie zmierzony.
Na zwykłym Windows + Chrome wynik jest wiarygodny; na Firefox/Safari pesymistyczny.

Emulatorów (RetroArch/PCSX2/Dolphin) aplikacja nie pobiera — `/retro` to hub linków.
Wyjątek: Flash — `/flash` ma wbudowany Ruffle 0.7.1 self-hosted
z `frontend/vendor/ruffle/` (offline, bez CDN). Przycisk pauzy to pauza —
Ruffle 0.7 nie daje API do głośności, więc nie ma udawanego mute.

## Baza

SQLite w WAL, tabele `offers` + `price_history`. Sesje i ciasteczka per host w
`~/.local/share/MatrixHunt/`, szyfrowane Fernet.

## Dane w `data/`

| Plik | Co to jest (zweryfikowane 2026-10-15) |
|---|---|
| `retro.json` | platformy 2, źródeł ROM 5, `archiveVault` 5 linków, delisted 3, flash 3 |
| `bookmarks.json` | kategorie zakładek (m.in. polskie serwisy gamingowe) |
| `seed_offers.json` | pusty (`[]`) — `load_seed_catalog()` nie dokłada nic |

`archiveVault` to odnośniki do kolekcji na archive.org, nie katalog gier.

## Znane ograniczenia

- itch.io zaparkowany: parser stawiał `price="Free"` bez sprawdzenia ceny
- `.app_settings.json` jawny (`PLAIN:`), gdy vault zablokowany
- `validate_image` skanuje pierwsze i ostatnie 4096 B
- `vault.unlock()` bez blokady, `write_bytes` nieatomowy
- proxy nieprzetestowane z prawdziwym logowaniem do sklepu
- pad: brak testów na realnym urządzeniu
- `backend/resolve_delisted_links.py` nie działa: importuje nieistniejący `scrapers/delisted.py`
- DLsite odrzucony jako źródło: sklep w większości 18+, brak publicznego API,
  gry głównie jako .exe do pobrania — wszystkie trzy rzeczy, których tu nie chcemy
- pełny `./weryfikuj.sh` przekracza 120 s (start serwera = scrape); `./sync.sh` wymaga celu (`./sync.sh <katalog>` lub `MIRROR_DIR=...`)
- historia: proxy zwracało kiedyś 403 na 3 sklepach (niezbadane, do powtórzenia)

## Weryfikacja

```bash
.venv/bin/python -m pytest tests/ -q
# 2026-10-15: 83 passed
```

Aktywne testy: `tests/test_ceny.py` + `tests/test_niezmienniki.py` (niezmienniki
na prawdziwych plikach/bazie) + `tests/test_niezalezne.py` (zachowanie kodu na
spreparowanych danych: logika cen, SSRF, migracja, martwe linki, offline, punktacja JS,
bramka 18+ w API i RSS, parser Łowców na sztucznym RSS).
Ten trzeci powstał po tym, jak 52 testy przechodziły przy żywym błędzie
(`Deal.price` domyślnie `"Free"` — zdublowane pole; już naprawione).
Stare `test_all.py` leży w `_testy_usuniete/test_all.py.bak` (poza repo).

---

Wersja 2.0 · Linux Mint 22.3 · Python 3.12
