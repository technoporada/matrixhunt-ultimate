cd /home/h5n1/Pulpit/katalog/Documents/matrixhunt-ultimate
A=/home/h5n1/Pulpit/katalog/Documents/tmpopencode/matrixhunt-ultimate
B=/home/h5n1/Pulpit/katalog/Documents/matrixhunt-ultimate
# _testy_usuniete/ holds the only copy of the removed test file. A previous
# --delete run emptied it because the directory was not excluded, so the
# exclusion is mandatory, not optional.
EXCLUDES=(
  --exclude=.venv
  --exclude=__pycache__
  --exclude=.pytest_cache
  --exclude='*.db'
  --exclude=.cookies
  --exclude=.app_settings.json
  --exclude=.session_secret
  --exclude=.vault_verifier
  --exclude=.filterlists
  --exclude=_testy_usuniete
  --exclude=sync.sh
)

# Trailing slash on both sides: without it rsync can decide a subdirectory is
# a separate transfer root and skip it, which silently left files stale in the
# mirror. Verified afterwards by hash, not by rsync's own idea of "up to date".
rsync -a --delete "${EXCLUDES[@]}" "$B/" "$A/"

skip_rel() {
  # Match on any path component, not just the leading one: the previous
  # version only tested prefixes, so backend/.filterlists/x.txt and
  # backend/.cookies/y.json slipped through and were reported as differences.
  case "/$1/" in
    */.venv/*|*/__pycache__/*|*/.pytest_cache/*|*/.filterlists/*|\
    */.cookies/*|*/_testy_usuniete/*) return 0 ;;
  esac
  case "$1" in
    .venv|__pycache__|.pytest_cache|.filterlists|.cookies|_testy_usuniete|\
    *.db|*.pyc|.app_settings.json|.session_secret|.vault_verifier|sync.sh) return 0 ;;
  esac
  # Per-machine state: each copy keeps its own session secret and settings,
  # so they are expected to differ and must never be mirrored.
  case "$1" in
    backend/.app_settings.json|backend/.session_secret) return 0 ;;
  esac
  return 1
}

fail=0
count=0
while IFS= read -r f; do
  rel="${f#"$B/"}"
  skip_rel "$rel" && continue
  count=$((count + 1))
  if ! cmp -s "$f" "$A/$rel"; then
    echo "  RÓŻNICA: $rel"
    fail=1
  fi
done < <(find "$B" -type f)

echo "  sprawdzono $count plików"
if [ "$fail" -eq 0 ]; then
  echo "lustro OK (wszystkie pliki zgodne bajt w bajt)"
else
  echo "lustro NIESPOJNE - patrz wyżej"
  exit 1
fi
