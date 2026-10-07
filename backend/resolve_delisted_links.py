"""One-time resolver: find a working Wayback Machine snapshot for every
delisted Steam appid and write the verified mapping to data/delisted_links.json.

Runtime scrapers must stay fast and offline-safe, so resolution happens here,
once, with results baked into the repo - never per-scrape.

Usage: ../.venv/bin/python resolve_delisted_links.py
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from scrapers.delisted import DELISTED_GAMES

OUT = HERE.parent / "data" / "delisted_links.json"
CACHE = Path("/tmp/opencode/delisted_cdx_cache.json")


def fetch_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "MatrixHunt-Ultimate/2.0 (link verification)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_text(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": "MatrixHunt-Ultimate/2.0 (link verification)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def available_snapshot(appid):
    """Closest snapshot via the availability API (cheap, one call)."""
    url = f"https://archive.org/wayback/available?url=store.steampowered.com/app/{appid}"
    try:
        d = fetch_json(url)
        snap = (d.get("archived_snapshots") or {}).get("closest") or {}
        if snap.get("status") == "200" and snap.get("url"):
            return snap["url"].replace("http://web.archive.org/", "https://web.archive.org/"), "available-200"
    except Exception as e:
        print(f"    available API error: {e}")
    return None, None


def cdx_latest(appid, cache):
    """Latest clean (200/text/html) capture via CDX.

    Delisted store pages mostly survive only as redirects (302 to the age
    gate), which replay unreliably. A 302 snapshot is worse than the plain
    Steam URL, so anything but a real 200 counts as a miss.
    """
    if appid in cache:
        return cache[appid]
    q = urllib.parse.quote(f"store.steampowered.com/app/{appid}", safe="")
    url = (f"https://web.archive.org/cdx/search/cdx?url={q}"
           f"&fl=timestamp,original,statuscode,mimetype"
           f"&filter=statuscode:200&filter=mimetype:text/html"
           f"&collapse=timestamp:6&limit=-3")
    try:
        lines = [ln for ln in fetch_text(url).splitlines() if ln.strip()]
        if lines:
            parts = lines[0].split(" ")
            ts, original = parts[0], parts[1]
            snap = f"https://web.archive.org/web/{ts}/{original}"
            cache[appid] = (snap, "cdx-200")
            return cache[appid]
    except Exception as e:
        print(f"    CDX error: {e}")
    # Do NOT cache failures: a transient 503 must not permanently mark the
    # appid as missing. Misses are retried on the next pass.
    return None, None


def main():
    done = {}
    if OUT.exists():
        try:
            done = json.loads(OUT.read_text()).get("links", {})
            print(f"resuming: {len(done)} already resolved", flush=True)
        except Exception:
            pass
    cache = {}
    if CACHE.exists():
        cache = {k: tuple(v) for k, v in json.loads(CACHE.read_text()).items()}

    resolved, missing = dict(done), []
    games = [g for g in DELISTED_GAMES if g.get("steam_appid") not in (None, "", "various")]
    print(f"resolving {len(games)} appids…", flush=True)
    for i, g in enumerate(games, 1):
        appid = g["steam_appid"]
        if appid in resolved:
            continue
        snap, how = available_snapshot(appid)
        if not snap:
            snap, how = cdx_latest(appid, cache)
            CACHE.write_text(json.dumps(cache, indent=1))
            time.sleep(1.0)  # be polite to the CDX endpoint
        else:
            time.sleep(0.4)
        if snap:
            resolved[appid] = {"url": snap, "via": how, "title": g["title"]}
            print(f"  [{i}/{len(games)}] {appid} OK ({how})", flush=True)
        else:
            missing.append({"appid": appid, "title": g["title"]})
            print(f"  [{i}/{len(games)}] {appid} MISS", flush=True)
        OUT.write_text(json.dumps({"links": resolved, "missing": missing}, indent=1))

    print(f"\nresolved: {len(resolved)}, missing: {len(missing)} -> {OUT}", flush=True)
    for m in missing:
        print("  MISS:", m, flush=True)


if __name__ == "__main__":
    main()
