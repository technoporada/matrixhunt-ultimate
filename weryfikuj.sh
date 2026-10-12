#!/usr/bin/env bash
# Jednorazowy skrypt weryfikacyjny. Uruchom ./weryfikuj.sh
cd "$(dirname "$0")" || exit 1

A=/home/h5n1/Pulpit/katalog/Documents/tmpopencode/matrixhunt-ultimate
B=/home/h5n1/Pulpit/katalog/Documents/matrixhunt-ultimate

# port zajety przez inna aplikacje? znajdz wlasny
for p in $(ss -tlnp 2>/dev/null | grep -oE '127.0.0.1:80[0-9]+.*pid=[0-9]+' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u); do
  kill "$p" 2>/dev/null
done
sleep 3

mkdir -p /tmp/opencode
( cd "$B/backend" && setsid ../.venv/bin/python main.py > /tmp/opencode/vp.log 2>&1 < /dev/null & )

for i in $(seq 1 40); do
  sleep 1
  grep -q "Uvicorn running" /tmp/opencode/vp.log 2>/dev/null && break
done

PORT=$(grep -oE "127\.0\.0\.1:[0-9]+" /tmp/opencode/vp.log 2>/dev/null | head -1 | cut -d: -f2)
echo "Serwer na porcie: ${PORT:-8000}"

"$B/.venv/bin/python" "$B/weryfikuj.py"
RC=$?

echo
echo "Serwer zostawiony dzialajacy. Zatrzymanie:"
echo "  kill \$(ss -tlnp 2>/dev/null | grep -oE '127.0.0.1:${PORT:-8000}.*pid=[0-9]+' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | head -1)"

exit $RC
