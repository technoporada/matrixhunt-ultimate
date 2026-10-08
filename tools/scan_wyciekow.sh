#!/usr/bin/env bash
# Sprawdza, czy w publicznym repo nie ma prywatnych ścieżek ani sekretów.
#
# Dodałem to po tym, jak trzy pliki z absolutnymi ścieżkami z katalogu
# domowego wylądowały w publicznym repo. Ten skrypt jest po to, żeby nie
# trzeba było o tym pamiętać.
#
# Uruchom przed wypchnięciem:  ./tools/scan_wyciekow.sh
set -u
cd "$(dirname "$0")/.." || exit 1

SKUTKI=0

echo "[1] Prywatne ścieżki"
# Tylko ścieżki pasujące do mojej maszyny. "~shared/do/~/click" z listy
# reklamowej to fałszywy alarm, więc nie dopasowuję goślepnie każdego "~".
TROJKI="/home/[a-z0-9]+/([A-Za-z0-9._-]+/)+|/home/[a-z0-9]+/[A-Za-z0-9._-]+|[A-Z]:\\\\Users\\\\[A-Za-z0-9._-]+"
# Skan tylko plików TRACKOWANYCH przez git. Pliki wykluczone w .gitignore
# zostają na dysku i nie wychodzą na GitHub — nie ma ich po co alarmować.
PLIKI=$(git ls-files | grep -v "^tools/scan_wyciekow.sh$")
WYNIK=$(grep -InE "$TROJKI" $PLIKI 2>/dev/null | head -10)
if [ -n "$WYNIK" ]; then
  echo "$WYNIK"
  echo "    ↑ ścieżka do katalogu użytkownika. Wyklucz w .gitignore i wywal z indeksu"
  SKUTKI=1
else
  echo "    czysto"
fi

echo "[2] Pliki, których nie wolno commitować"
for plik in .session_secret .vault_verifier .cookies .app_settings.json; do
  if git ls-files --error-unmatch "$plik" >/dev/null 2>&1; then
    echo "    ⚠ $plik jest w gicie"
    SKUTKI=1
  fi
done
[ "$SKUTKI" = "0" ] && echo "    brak plików sesyjnych w gicie"

echo "[3] Rozmiar tego, co pójdzie do repozytorium"
du -sh --exclude=.git --exclude=.venv . 2>/dev/null | awk '{print "    " $1}'

exit "$SKUTKI"
