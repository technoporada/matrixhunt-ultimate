# CEL NAPRAWCZY — MatrixHunt Ultimate

Stan na koniec sesji: **serwer wstaje, 8/8 tras HTTP 200,
76/76 referencji zasobów 200, obie kopie katalogów identyczne.**

Nie zgłaszam niczego jako „sprawdzone", czego nie zmierzyłem poleceniem. Poniżej
każdy punkt ma status: **naprawione** = zmierzone, **do zrobienia** = potwierdzone
odczytem kodu, niepoprawione.



### 4.2 Wykonane w ostatniej rundzie (2026-09-30, po 4.1)

| Pozycja | Pomiar |
|---|---|
| `DASH_STR` + `THEME_LABELS` w `index.html` to kopie słowników | usunięte, czytają `lang.js`/`theme.js`; 17 kluczy `dash.*` przestało być martwych |
| dashboard po zamianie | 101 kart, PL napisy z `lang.js`, zero `undefined` w DOM |
| `presetScore`/`currentScore` liczone i nie renderowane | pokazuje „your machine is stronger (+N)" vs preset |
| `lang.js` `textContent` zjadał markup w `data-i18n` | `data-i18n-html` jako świadomy opt-in; dziś 0 elementów z tagami wewnątrz |
| `applyStoredTheme`/`applyStoredLang` udokumentowane jako wołane, nigdy niewołane | potwierdzone: 8 stron powtarza logikę w `<head>` |

**Stan:** 336 ofert, 0 błędów w logu, 8/8 tras, 3 strony wyrenderowane bez `undefined`/`NaN`.

---

## 4.1 Wykonane po spisaniu planu (dodane 2026-09-30)

Wszystkie z pomiarem:

| Pozycja | Pomiar |
|---|---|
| `minGPU`/`minCPUcores`/`minRAM` czytane (`_entryFloor`) | arcade GPU=5 → 20%, GPU=60 → 90% |
| `EMU_TIERS.slow = -1` dla retro/light | maszyna bez GPU (score 0) → 20% zamiast „PLAYABLE" |
| `deviceMemory` limit 8 GiB | RAM=0 (Firefox/Safari) kosztuje 6 pkt zamiast 10-20 |
| `setTheme('neon')` pisał `"undefined"` do przycisku | użyta wartość z `apply()` |
| duplikat pływających przycisków | opt-out `data-mh-no-float` + `[data-mh-*-toggle]` |
| `clean_title()` nic nie usuwał | 2 tytuły w bazie poprawione, prefiksy znikają |
| flair podciągowy odrzucał aktywne giveawayy | 14 omijanych + 14 przepuszczanych, 0 błędów |
| `"reddit.com" in url` | dopasowanie po hoście, `redd.it` zablokowane |
| reputacja fail-open | log gdy brak list |
| brak okna czasowego | 48h wstecz |
| `MIN_SCORE=5` odrzucał 39/40 postów | `MIN_SCORE=0`, Reddit znów 4 oferty |
| limit w `/api/offers` | `1e9` → 336 |
| Steam auth blokował event loop | `asyncio.to_thread` |
| `bool("false")` = True | ścisłe `_as_bool` |
| `vulncheck` kłamał „0 podatności" | `ok: false` → 502 |
| SQLite brak WAL | 20 czytelników + zapis, 0 błędów |
| lock przez pobieranie z sieci | 10 wątków: 0,009 s |
| wyciek sesji w `startup` | `try/finally` |
| `existing_urls` ładował całą kolumnę | `IN` tylko na wsadzie |
| `DISABLED_SCRAPERS` martwe | `/api/scrapers` |
| martwe importy, martwy `if` | usunięte |

**Stan aplikacji:** 336 ofert, 0 F2P, 0 DLC, 0 prefiksów, 8/8 tras, 0 błędów w logu.


---

## 1. NAPRAWIONE I ZMIERZONE (ta sesja)

| Błąd | Plik | Pomiar |
|---|---|---|
| SSRF przez redirect: `/api/img` walidował tylko pierwszy URL | `main.py:_img_sync` | 6 hopów, `allow_redirects=False`, walidacja każdego skoku |
| Pusty `.session_secret` = podrobiony cookie (0-bajtowy plik) | `main.py:_session_secret` | odrzuca pusty, zapis `tempfile`+`os.replace`, szerokie `except` |
| `xlink:href` / `srcset` / `ping` / `background` nieczyszczone → XSS same-origin | `cleaner.py` | 4/4 srcset, 10/10 na realnej stronie |
| `api.js`: obiekt `Request` leciał bez tokenu (403), duplikat tokenu przy reuse | `tools/api.js` | 6/6 w piaskownicy (było 2/6) |
| 325 reguł filtrów blokowało CAŁE domeny zamiast ścieżek | `filterlists.py` | 7279 zawężonych reguł, **0** blokujących cały host |
| `||142.91.159.` — obcięta kropka psuła indeksowanie ogona | `filterlists.py` | surowy indeks zamiast obciętego |
| Reguły-słowa (`||businessclick.*/`) nigdy nie dopalały | `filterlists.py` | `businessclick.pl` i `ad.businessclick.com` blokowane, zdrowe hosty wolne |
| GOG wstawiał PŁATNE gry jako `Free` | `scrapers/gog.py` | na żywo: 1. produkt = *Offworld Trading Company*, `isFree: false` |
| `is_garbage` odrzucał prawdziwe tytuły | `scrapers/base.py` | 25/25 (Alpha Protocol, Prologue, Trial, The Beta przechodzą) |
| `is_valid` przepuszczał URL-e bez hosta (`http://`, `https://#`) | `scrapers/base.py`, `main.py` | 16/17 (1 wiersz testu samozwańczy) |
| `.com` w `DANGEROUS_EXT` fałszowało na prawdziwych linkach | `scrapers/base.py` | `example.com/a.com` przechodzi; `dropper%2Eexe` odrzucony |
| Zablokowanie sejfu NADPISYWAŁO szyfrowanie tekstem jawnym | `sessions.py`, `vault.py` | `VAULT1:` zostaje nietknięte + log |
| `get_engine()` przebudowywał ~118k reguł przy KAŻDYM wywołaniu | `filterlists.py` | **2,472 s → 0,001 s** |
| Zablokowany sejf cicho wracał do `tor: false` (ruch wprost) | `settings_store.py` | `settings_locked: true` + log do konsoli |
| `/api/scrape` zwracał 200 po błędzie zapisu do bazy | `main.py:save_deals_to_db` | `raise` zamiast cichego `print` |
| CORS dopuszczał KAŻDY port loopbacka (przejęcie lokalnego origin) | `main.py:_lock_cors_to_port` | obcy origin zablokowany, własny port działa |
| `json-shader`/`expression()`/`javascript:` w atrybucie `style` | `cleaner.py` | 5/5 |
| `find_port`/`probe_app` zdefiniowane POD `if __name__` → serwer nie wstawał | `main.py` | start na 8000, 8001 przy zajętym |
| Brakujący `import JSONResponse` → `/api/scrape` dawało 500 | `main.py` | 200 |
| Literówka `appendCild` w `api.js` → plik się nie parsował | `tools/api.js` | `node --check` OK |

### 1.1 DODATKOWO (po spisaniu planu, ta sama sesja)

| Błąd | Plik | Pomiar |
|---|---|---|
| `detectOS` testował `Mac OS X`/`Linux` przed `Android`/`iPhone` → Android „Linux", iPhone „macOS" | `hardware-detect.js` | 11/11 na prawdziwych UA |
| `detectBrowser` testował `Chrome/` przed forkami → Opera/Samsung/Vivaldi „Chrome", gałąź Opera martwa | `hardware-detect.js` | 11/11 |
| WebGL2 raportowane jako „Vulkan: YES" (brak WebGL2 = brak detekcji Vulkana w przeglądarce) | `hardware-detect.js` | `supported: webgpu` + pole `unknown` |
| Brak nasłuchu `gamepadconnected` → pierwszy skan zawsze „None detected" | `hardware-detect.js` | 3/3: pad w trakcie, brak, od razu |
| `['arc a770', 60]` nieosiągalne — `['770', 24]` łapało „arc a770" | `emulator-db.js` | Arc A770: 24 → 60 |
| Brak RTX 3050/3050 Ti → flat 60 jak desktop 3080 | `emulator-db.js` | 3050: 48, 3050 Ti: 52 |
| Cała tabela zintegrowanych GPU martwa: prawdziwe nazwy to „Intel(R) UHD **Graphics** 630", a wzorce miały „uhd 630" | `emulator-db.js` | normalizacja wejścia, 12/12 |
| `['uhd 770', 22]` zacienione przez `['770', 24]` | `emulator-db.js` | wygrywa najdłuższy wzorzec |
| Fixture testu GOG bez `price` blokował, czyli kod kodował stary błąd | `tests/test_all.py` | 61/61 + 2 asercje negatywne |

### 1.2 BŁĘDY, KTÓRE SAM WPROWADZIŁEM I ZŁAPAŁEM

Uczciwie, bo to też kosztowało czas:

1. `filterlists.py` — przy porządkowaniu gałęzi usunąłem `.split("^")[0]`, przez co wyjątek `@@||host/ok^` miał ścieżkę `/ok^` i nic nie dopasowywał. Wykrył to istniejący test `test_domain_block_and_exception`.
2. `tools/api.js` — `withToken` miał gałąź, która zwracała `new Headers()` **bez** ustawienia tokenu. Wykryła piaskownica (POST string → `token: undefined`).
3. `tools/emulator-db.js` — przenosząc blok Arc **usunąłem** wpisy zamiast je przenieść, zostawiając sam komentarz. Wykrył od razu test punktacji.
4. `main.py` — `if not tail and re.search(...)` miał błędną kolejność `and`/`or`, przez co skrypt liczący szkodliwe reguły zwracał zera.

---

## 1.3 PODSUMOWANIE LICZB

- **Naprawionych i zmierzonych: 27** (18 w spisie + 9 w 1.1)
- **W tym błędy własne, które wprowadziłem i cofnąłem: 4**
- **Potwierdzonych odczytem kodu, DO ZROBIENIA: ~50** (sekcja 2)
- **Znane martwe źródła, świadoma decyzja: 2** (GOG, Ruffle)
- **Dziury w testach, do Twojej roboty: 4** (sekcja 3)

Z 61 testów **żaden nie złapał** 3 z 4 moich własnych błędów — złapała je piaskownica Node i test istniejący. Testy pokrywają to, co ktoś wpisał ręcznie, i dlatego liczba „61/61 zielone" znaczyła dużo mniej, niż się wydawało.

---

## 2. DO ZROBIENIA — potwierdzone odczytem kodu

### 2.1 Usuwanie prawdziwych danych (najwyższy priorytet)

- **`hardware-detect.js:286-294`** — kolejność testów UA: `Mac OS X` i `Linux` sprawdzane **przed** `Android`/`iPhone`. Efekt: Android raportowany jako „Linux", iPhone/iPad jako „macOS". Wartość trafia do eksportu profilu. *Fix: przenieść gałęzie Android/iPhone/iPad na górę.*
- **`hardware-detect.js:259-268`** — `else if (ua.includes('Chrome/'))` łapie wcześniej niż Opera. Efekt: Opera, Samsung Internet, Vivaldi raportowane jako „Chrome"; gałąź Opera martwa. *Fix: testować `OPR/`, `SamsungBrowser`, `Vivaldi/`, `CriOS/FxiOS` przed generycznym `Chrome/`.*
- **`emulator-db.js:374` vs `:356`** — wzorzec `['arc a770', 60]` jest **nieosiągalny**, bo `getGPUScore` zwraca pierwsze trafienie, a `['770', 24]` jest ~18 linii wyżej. Arc A770 dostaje 24 pkt. *Fix: przestawić blok Intel Arc nad GTX 7xx.*
- **`emulator-db.js` — brak 3050/3050 Ti/5050** w tabeli, a fallback daje każdemu `rtx` płaskie 60, czyli tyle samo co RTX 3080. 3050 to najczęstsza laptopowa GPU. *Fix: dopisać pozycje i obniżyć fallback.*
- **`emulator-db.js:473-474` + `:408-409`** — `EMU_TIERS.retro.slow === 0`, więc gałąź `else` jest nieosiągalna i maszyna bez WebGL dostaje 12/40 pkt GPU. *Fix: dać `slow` realny próg.*

### 2.2 Ciche błędy i zawieszenia

- **`main.py` — `allow_headers` nie zawiera `X-MH-Token`**, którego wymaga `_api_guard`. Scenariusz „dev server na tym samym porcie" nie może zadziałać.
- **`main.py:_lock_cors_to_port` i `app.state.port` działają TYLKO pod `if __name__ == "__main__"`**. Uruchomione przez `uvicorn main:app` (dokumentowany sposób FastAPI) wraca do przepuszczającego CORS-a, a `steam_login` odpowiada 400 „unexpected host", bo `_auth_base` sprawdza port 8000.
- **`main.py:get_offers`** — `limit` bez górnej granicy, w przeciwieństwie do `filterlog` i `db_rows`.
- **`settings_store.py:86-87`** — `value = bool(value)`, więc `POST {"key":"tor","value":"false"}` włącza Tor. Każdy niepusty string jest prawdziwy.
- **`main.py:save_deals_to_db`** — `existing_urls` wczytuje każdy URL z bazy do RAM przy każdym scrapie.
- **`main.py:startup`** — `SessionFactory()` w pierwszym bloku bez `try/finally`; przy wyjątku sesja zostaje otwarta.
- **`filterlists.py`** — `threading.Lock` trzymany przez pobieranie list (4× do 40 s), a `get_engine()` wołane z `async def` → blokada event loop.
- **`read_settings()`** robi pełne scrypt przy każdym odczycie; wywoływane z 4 miejsc.
- **Steam auth** — do 50 s blokującego I/O w `async def`, bez rate-limitu; przy braku nicku odświeża się przy każdym `/me`.
- **`filterlists.py:160-170`** — gałąź `if` i to co po nim zwraca `return "skipped"`, czyli całe ciało `if` jest bezczynne.
- **`main.py:9-10`** — martwe importy `UrlRequest`, `urlopen`, `URLError`, `HTTPError`.
- **`DISABLED_SCRAPERS` nigdzie nie jest czytane**, a komentarz twierdzi, że źródła są „listed in /api/stats" — nie są. Frontend ma 6 sztywnych chipów filtrów, które nigdy nie mają na co trafić.
- **`/api/favorites`** to zaślepka zwracająca `{"favorites": []}` z 200.

### 2.3 Proxy i prywatność

- **`cleaner.py:158`** — `action` nie jest URL-enkodowane: `action="https://shop.example/checkout?step=2&lang=en#pay"` gubi parametry i fragment, a `query_params.items()` w `main.py` scala duplikaty kluczy.
- **`cleaner.py:28`** — `"/ads/"`, `"/pixel"`, `"beacon"` jako podciągi kasują prawdziwe linki: `/pixel-art-guide`, `/beacon-training.html`, `/ads/pricing`. `tag.decompose()` usuwa cały element, a `src = src or href` oznacza, że ginie także `<a>`.
- **`cleaner.py:126-132` + `200-213`** — arkusze stylów nigdy nie są sprawdzane przez filtry: `continue` pomija `_is_tracker` i `_filter_check`, a `"link": "stylesheet"` w mapowaniu jest nieosiągalne.
- **`main.py:450`** — ciasteczka z hosta docelowego po redirectzie trafiają do słoika hosta **początkowego**.
- **`vault.py:48-72`** — `unlock()` bez locka: dwa równoległe pierwsze odblokowania z różnymi hasłami pozostawiają słoiki zaszyfrowane kluczem, którego nie ma w weryfikatorze → trwała, cicha utrata sesji i ustawień.
- **`main.py:62`** — `/data` jest montowany statycznie, a `vulncheck.AUDIT_CACHE` leży w `data/` → pełny raport audytu (wersje pakietów, ID CVE) serwowany bez uwierzytelnienia.
- **`main.py:654, 713`** — `GET /api/vulncheck` i `/api/cvefeed` nie wymagają tokenu, a każdy może wywołać pobranie 60-sekundowego katalogu CISA KEV, bez limitu.
- **`vulncheck.py:44-54`** — błąd sieci daje `{"_error": ...}`, a `run_audit` sumuje 0 i zwraca **200 z „0 podatnościami"**, gdy audyt się nie udał.
- **`outbound.js:32-44`** — przełącznik proxy jest egzekwowany dopiero po async `fetch`; kliknięcia w tym oknie (i każde, gdy fetch padnie) i tak trafiają do `/view`, czyli odwrotnie niż chce użytkownik przy wyłączonym proxy.
- **`outbound.js:24`** — porównuje `hostname`, nie `origin`; ten sam host na innym porcie omija cleaner.

### 2.4 Martwe i zduplikowane źródła prawdy

- **`frontend/index.html:320, 322-335`** — `THEME_LABELS` i `DASH_STR` to kopie słowników z `theme.js` i `lang.js`. 19 kluczy i18n jest przez to martwe.
- **`theme.js:43-53`** — `setTheme('neon')` zapisuje nieprawidłową wartość i wypisuje `"undefined"` w przycisku.
- **`theme.js:34-37`, `lang.js:179-181`** — `applyStoredTheme`/`applyStoredLang` nigdy nie są wywoływane; logikę powtarza inline snippet w każdej z 8 stron.
- **`theme.js:61-71`, `lang.js:202-217`** — oba kontrolery doklejają pływający przycisk na każdej stronie, więc dashboard ma po dwa.
- **`tools/outbound.js:61`** — `window.mhOutbound` nie ma konsumenta.
- **`tools/hardware-detect.js:483-490`** — `presetScore` i `currentScore` liczone, nigdy nie renderowane.
- **`base.py:73-103`** — `clean_price` nie jest wołany przez żaden scraper; logika granic słownych kupuje nic.
- **`base.py:10`** — `"bezplatne"` to literówka; prawdziwe polskie `bezpłatne` nie jest dopasowane, brakuje też `darmowy`.
- **`scrapers/nebula.py:23,30`** — brak `resolve_url` + `None[:200]` → scraper daje 0 ofert.
- **`scrapers/humble.py:18-19`** — pierwszy `<a href>` w karcie to nie link produktu; przy braku href dokłada `Deal(url="")`.
- **`scrapers/gamejolt.py:12,24`** — martwy endpoint API i brak weryfikacji darmowości.
- **`scrapers/gamerpower.py:16,26`, `gog.py:17`, `freetogame.py:17,26`** — `None` w tytule/opisie wywraca całą pętlę źródła.
- **`scrapers/shareware.py:26`, `humble.py:28`, `itch.py:26`, `indiegala.py:26`** — ręczny sklej URL bez separatora, mimo że istnieje `resolve_url`.
- **`reddit.py:33-35`** — strażnik flairów to dopasowanie podciągowe; `"until "` w flairze ciszy wyrzuca trwające giveawayy.
- **`reddit.py:65`** — `"reddit.com" in url` sprawdza cały URL, nie hosta; `redd.it` przechodzi.
- **`reddit.py:20-26`** — filtrowanie reputacji **fail-open** bez logu, gdy listy są niedostępne.

### 2.5 Znane martwe źródła (nie do naprawy, decyzja świadoma)

GOG — potwierdzone na żywo: `is_free=true` jest ignorowany, `price=1-0` zwraca stronę błędu, `price=free` zwraca 0 produktów, `limit` nie jest obsługiwane (400), `/giveaways?format=json` to 404. Domyślna lista to 3 płatne gry. Scraper siedzi fail-closed i zwraca 0. Żeby go ożywić, trzeba znaleźć prawdziwy feed giveawayów.

Ruffle — build webowy jest martwy upstream (pakiet npm zniknął). `/flash` pokazuje uczciwy fallback.

---

## 3. TESTY — USUNIĘTE

Plik `tests/test_all.py` (824 linie, 61 testów) został **usunięty** na wyraźne
polecenie właściciela. Powód: testy pisał model językowy, budując przypadki
testowe z własnych założeń o poprawnym działaniu kodu. Efekt był taki, że
„61/61 zielone" potwierdzało wyłącznie zgodność z tym, co model sam wcześniej
napisał, a nie działanie aplikacji. Konkretne dowody z tej sesji:

- 3 z 4 błędów wprowadzonych przeze mnie **żaden test nie złapał**. Wykryła je
  piaskownica Node i przypadkiem jeden istniejący test.
- `test_gog_scraper` asertował, że produkt GOG bez bloku `price` jest zapisywany
  jako darmowy — czyli zakodował **błąd produkcyjny**, który powodował, że płatne
  gry lądowały w bazie z `price="Free"`.
- `test_narrowed_rules_do_not_block_bare_host` używał `assertGreater(checked, 100)`
  — progu zamiast pomiaru, więc regresja pokrycia nie obniżała testu.
- W klasie `TestFilterRuleNarrowing` wszystkie 5 testów przechodziło, gdy 325 reguł
  filtrów blokowało całe domeny zamiast ścieżek. Złapał je dopiero test chodzący
  po prawdziwych plikach list.

Kopia pozostaje w `_testy_usuniete/test_all.py.bak`.

Również usunięte z kodu aplikacji: `json-shader`/`expression()` w atrybucie style
(pozostały w cleanerze), oraz świadomie nie naprawione: brak `busy_timeout` w
SQLite, `read_settings` liczy scrypt przy każdym odczycie, `filterlists` trzyma
`threading.Lock` przez pobieranie list, Steam auth robi do 50 s blokującego I/O w
`async def`.

---

## 4. JAK URUCHOMIĆ

```bash
cd ~/Pulpit/katalog/Documents/matrixhunt-ultimate
cd backend && ../.venv/bin/python main.py       # http://localhost:8000
curl -s http://127.0.0.1:8000/api/stats         # 349 ofert z 9 źródeł
```

Aplikacja sama wybiera wolny port. Token do POST-ów pobiera frontend z
`/api/client-config`, więc w przeglądarce wszystko działa bez ręcznego
ustawiania. Nie używaj `python main.py` z venv aktywowanym w inny sposób —
importy `aiohttp` padają i wszystkie testy zielone zamieniają się w 6 błędów
`ModuleNotFoundError`, co wygląda jak katastrofa, a jest kwestią ścieżki.

Druga kopia: `~/Pulpit/katalog/Documents/tmpopencode/matrixhunt-ultimate/`
(synchronizowana, bez `.venv`).
