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

## Co faktycznie działa

| | Stan |
|---|---|
| Oferty w bazie | **64**, z 5 źródeł |
| Scrapery aktywne | **6** (GamerPower, Epic, Steam, GOG, IndieGala, Reddit) |
| Scrapery zaparkowane | **8** (zwracały 0 albo timeoutowały) |
| Kolumna `price` | **wszystkie 64 rekordy mają `'Free'`** |
| Stan faktyczny | kolumny `price` nie rozróżniają „sprawdzone" od „nie sprawdzone". Żadna oferta w tej bazie nie ma potwierdzenia ceny z API sklepu. |

**Żadna z 64 ofert nie jest potwierdzona jako darmowa.** `price='Free'` to
wartość wpisana przez scraper, nie wynik sprawdzenia strony sklepu.
Potwierdzenie wymaga otwarcia każdej strony i przeczytania treści.

## Strony

`/` dashboard · `/retro` emulator · `/pad` test pada · `/db` podgląd bazy
`/view` proxy stron · `/wiki` · `/bookmarks` · `/flash`

## API

30 tras. Pełna lista: `grep -oE '@app\.(get|post)\("[^"]+"' backend/main.py`

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

Aplikacja nie pobiera emulatorów i nie integruje się z żadnym.

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

## Znane ograniczenia

- `reason` w `/api/scrapers` zwraca `null` — UI nie powie, dlaczego scraper
  jest zaparkowany
- itch.io zaparkowany: parser stawiał `price="Free"` bez sprawdzenia ceny
- `.app_settings.json` jawny, gdy vault zablokowany
- `validate_image` skanuje pierwsze i ostatnie 4096 B
- `vault.unlock()` bez blokady, `write_bytes` nieatomowy
- proxy nieprzetestowane z prawdziwym logowaniem do sklepu
- pad: brak testów na realnym urządzeniu, bo nie było sprzętu w środowisku

## Weryfikacja

```bash
./weryfikuj.sh
```

Stan z ostatniego uruchomienia: **37 z 42 przeszło.**

Nieudane — proxy zwraca **403 na wszystkich trzech sklepach**:

```
proxy zwraca 200            403
www.gog.com przez proxy     403, 0B
itch.io przez proxy         403, 0B
www.humblebundle.com        403, 0B
```

Te same sprawdzenia kilka godzin wcześniej przechodziły (GOG 663 kB, itch.io
106 kB, Humble 24 kB). Przyczyna niezbadana — albo sklepy zaczęły blokować,
albo zmieniłem coś w sesjach albo w UA. **Nie wiem która.** Dopóki nie jest
zbadane, proxy nie jest potwierdzone jako działające.

Testy jednostkowe zostały usunięte. Nie zastąpiłem ich nowymi —
napisane przez tego samego model, który napisał kod, potwierdzają tylko to,
co ten model już wiedział.

---

Wersja 2.0 · Linux Mint 22.3 · Python 3.12
