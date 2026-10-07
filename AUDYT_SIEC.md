# GDZIE TEN KOD WYCHODZI DO SIECI

Audyt wykonany na plikach, nie deklarowany. Wszystko poniżej to lista, nie
opinia. Weryfikowalne: każdy punkt ma plik i linię.

Wykonane: `./.venv/bin/python`, `grep`, bez uruchamiania ruchu sieciowego poza
pobraniem filtrów i odpowiedzi testowych.

---

## 1. HOSTY, DO KTÓRYCH APLIKACJA SIĘ ŁĄCZY

Sklepy i źródła danych — to po to istnieje aplikacja:

```
www.gamerpower.com          store.steampowered.com    steamcommunity.com
www.gog.com                 store.epicgames.com       itch.io
freebies.indiegala.com      www.humblebundle.com      www.freetogame.com
www.freesteamkeys.com       sharewareonsale.com       games.nebula.app
gamejolt.com                giveawayradar.com         www.reddit.com
arctic-shift.photon-reddit.com                       web.archive.org
archive.org                 raw.githubusercontent.com
```

Listy filtrów (subskrypcje, odświeżane co 24 h):
```
easylist.to
```

Audyt bezpieczeństwa (tylko po Twoim kliknięciu):
```
api.osv.dev                  www.cisa.gov              check.torproject.org
```

Logowanie Steam:
```
steamcommunity.com           specs.openid.net
```

**Nie ma w kodzie:** żadnego hosta analitycznego, telemetrycznego, żadnego
LLM/AI API, żadnego webhooka, webhooks.discord, ngrok, requestbin, pipedream.
Sprawdzone grepem po `google-analytics`, `googletagmanager`, `gtag`, `segment.io`,
`mixpanel`, `amplitude`, `sentry`, `datadog`, `openai`, `anthropic`, `huggingface`,
`cohere`, `ollama` — jedyne trafienia to nazwy w filtrach reklamowych EasyList,
czyli lista reguł blokujących, nie kod analityczny.

---

## 2. CO Wychodzi Z TWOJEGO WEJŚCIA (proxy `/api/clean`)

To jest **jedyny** endpoint, przez który Twoje dane mogą wyjść do sklepu.

- `backend/main.py:479` `_clean_sync` — pobiera stronę przez `requests`
- `backend/main.py:483-486` — formularz POST jest przekazywany do sklepu
  **w całości**, razem z wpisanym hasłem. To jest po to, żeby logowanie działało
  przez viewer. Hasło leci do sklepu, do którego go wpisałeś, i nigdzie indziej.
- `backend/main.py` `persist_from_requests` — z odpowiedzi zapisuje **tylko
  `Set-Cookie`**, nigdy treść formularza. Sprawdzone w `backend/sessions.py:save_jar`.
- Ciasteczka leżą w `backend/.cookies/` jako pliki per host, uprawnienia 0600.

Jeśli nie używasz proxy, ten kod nie ma jak z Twojego komputera wyjść — nic
poza odpytywaniem sklepów po oferty.

---

## 3. CO SIEDZI NA DYSKU

| Plik | Rozmiar | Uprawnienia | Zawartość |
|---|---|---|---|
| `backend/.session_secret` | 216 B | 0600 | klucz podpisu ciasteczka sesji (zaszyfrowany lub `PLAIN:`, patrz niżej) |
| `backend/.app_settings.json` | 191 B | 0600 | twoje ustawienia proxy/Tor/list filtrów |
| `backend/.cookies/*.json` | — | 0600 | ciasteczka per witryna, tylko gdy się zalogujesz przez viewer |
| `backend/matrixhunt.db` | — | 0640 | publiczne oferty, jawny tekst z założenia |
| `backend/.filterlists/*.txt` | — | 0660 | EasyList, EasyPrivacy, polskie filtry, badware |
| `backend/.kev.json` | 1,4 MB | 0600 | katalog CVE CISA KEV |

**Uwaga, którą sam znalazłem:** `.app_settings.json` leży jako `PLAIN:` — twoje
ustawienia nie są zaszyfrowane, mimo że sejf istnieje i `.session_secret` jest
zamknięty. Powód: przy pierwszym uruchomieniu zablokowany sejf zapisuje
ustawienia jawnie, a mój strażnik pilnuje tego tylko dla ciasteczek, nie dla
ustawień. Nie naprawiłem tego, bo to decyzja: przy zablokowanym sejfie ustawienia
mają być nieczytelne (proxy przestaje działać) czy zapisywane jawnie (to co jest
teraz).

---

## 4. CO NIE ROBI

| Nie ma | Sprawdzone |
|---|---|
| wysyłania czegokolwiek na zewnątrz poza listą z punktu 1 | grep po webhook/ngrok/discord/telegram/beacon/telemetry |
| logowania Twojej aktywności gdziekolwiek | brak kodu analitycznego |
| wysyłania haseł poza sklep, do którego je wpisałeś | `main.py:479-486` |
| automatycznych pobrań w tle poza odświeżeniem list filtrów | `_maybe_refresh_background` w `filterlists.py` |
| testów, które odpalałyby się same w tle | `tests/` usunięte, kod ich nie dotyka |

---

## 5. CZEGO NIE SPRAWDZIŁEM

Podaję, żeby ta lista nie udawała kompletności:

- **Nie uruchamiałem aplikacji pod ruchem sieciowym i nie monitorowałem pakietów.**
  Analiza jest statyczna — czytanie kodu. Dynamicznie (wireshark/tcpdump) nie
  robiłem.
- **Nie sprawdzałem skryptów vendored** (`frontend/vendor/`): React 18.3.1,
  ReactDOM, Babel — pliki pobrane wcześniej, weryfikacja sumy kontrolnej
  nie była przeze mnie robiona.
- **Nie sprawdzałem `/tmp/opencode/`** — to moje katalogi robocze, poza
  projektem.
- **Proxy nie przeszło przez prawdziwy sklep z prawdziwym logowaniem.**
  `example.com` nie ma formularza ani ciasteczek. Maszyneria jest napisana, ale
  nie była przetestowana end-to-end z prawdziwym kontem.
- **Nie czytałem swojego własnego kodu źródłowego** i nie mam jak — wiem
  tyle, ile widać z zewnątrza procesu.
