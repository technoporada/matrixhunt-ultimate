# Security Policy

## Zgłaszanie problemów

Jeśli znajdziesz podatność, otwórz **prywatny** security advisory w repozytorium
GitHub (Security → Advisories) albo napisz do autora. Nie publikuj exploita,
zanim poprawka nie trafi do `main`.

## Model bezpieczeństwa

MatrixHunt Ultimate to **aplikacja lokalna** — działa na `127.0.0.1`,
zero chmury, zero CDN. React, Babel i Ruffle są zvendorowane w `frontend/vendor/`.

### Co aplikacja robi w sieci (tylko na żądanie)

- Odpytuje sklepy/agregatory po oferty (GamerPower, Epic, Steam, GOG, itch.io, …)
- Pobiera listy filtrów (EasyList i spółka) co 24 h
- Audyt zależności (OSV + CISA KEV) — tylko po kliknięciu „Sprawdź” w `/api/vulncheck`
- Sprawdza Tor (`check.torproject.org`) — tylko jeśli włączysz tryb Tor

**Nie ma** telemetrii, analityki, webhooków, LLM API. Audyt statyczny w `AUDYT_SIEC.md`.

### Zabezpieczenia

- **SSRF**: `/api/clean` blokuje `localhost`, `127.0.0.1`, `169.254.x.x`, `file://` i inne prywatne adresy.
- **XSS**: wszystkie tytuły/opisy z trzecich stron są sanityzowane; skrypty i `on*=` usuwane (weryfikuj.py sprawdza).
- **Path traversal**: `/data/...` blokuje `..` i dostęp do plików poza `data/`.
- **CSRF**: cross-origin `Origin` blokowany na `/api/clean` i `/api/img`.
- **Token sesji**: zapisy wymagają nagłówka `X-MH-Token` z `/api/client-config` (losowany na start).
- **CORS**: `allow_origins=[]` — obcy origin nie dostaje nagłówków.
- **Ciasteczka**: per-host w `backend/.cookies/`, uprawnienia `0600`.
- **Session secret**: `backend/.session_secret`, uprawnienia `0600`.

### Znane ograniczenia

- `.app_settings.json` jest zapisywany jawnie (plaintext), gdy sejf jest zablokowany.
  Strażnik pilnuje tego tylko dla ciasteczek, nie dla ustawień.
- Vendored pliki (React, Babel, Ruffle) nie są weryfikowane sumą kontrolną
  (sprawdzone ręcznie przy dodaniu, nie automatycznie).
- Proxy `/api/clean` przekazuje formularze POST w całości do sklepu
  (w tym hasła) — to konieczne, żeby logowanie przez viewer działało.

### Zależności

- `pip-audit` / `osv-scanner` do audytu: uruchom `./.venv/bin/python -m pip install pip-audit`
  albo użyj `arek-bootstrap --install`.
- `certifi>=2026.10.23` — aktualne CA (incydent eMudhra/emSign, X 2026).
- Zaktualizuj pip przed instalacją: `.venv/bin/python -m pip install --upgrade pip`

### Pobieranie gier

MatrixHunt Ultimate **nie pobiera i nie uruchamia gier**. Linkuje do stron sklepów.
Pobieranie i uruchamianie gier to Twoja odpowiedzialność — pobieraj tylko z oficjalnych
źródeł (Steam, Epic, GOG, itch.io). Aplikacja ostrzega, że żadna oferta nie ma
potwierdzonej ceny z API sklepu.

### Weryfikacja

```bash
./weryfikuj.sh   # 42/42 sprawdzeń (SSRF, XSS, traversal, filtry, F2P, wyciek)
```
