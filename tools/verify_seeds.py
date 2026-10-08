"""Verify seed-catalog candidates. Steam appids go through the official
store API (accurate free-status, not just HTTP 200); Epic/standalone sites
get a page check. Only verified entries are printed as JSON.
"""
import json
import time
import urllib.request

UA = {"User-Agent": "MatrixHunt/2.0 (free games aggregator)",
      "Accept-Language": "en-US,en;q=0.9"}

STEAM_IDS = [570, 440, 230410, 238960, 730, 1172470, 578080, 1085660, 1599340,
             2357570, 2767030, 2507950, 2943650, 1222670, 1665460, 1782210,
             1677740, 1240440, 1286830, 1284210, 8500, 109600, 9900, 24200,
             218230, 386360, 394360, 813810, 291550, 2073850, 2139460, 336530,
             236390, 386260, 1120680, 823130, 438100, 471710, 2051620]

PAGES = [
    ("Fortnite", "https://store.epicgames.com/en-US/p/fortnite", "shooter", "Fortnite"),
    ("Rocket League", "https://store.epicgames.com/en-US/p/rocket-league", "sports", "Rocket League"),
    ("Fall Guys", "https://store.epicgames.com/en-US/p/fall-guys", "action", "Fall Guys"),
    ("League of Legends", "https://www.leagueoflegends.com/en-us/", "moba", "League of Legends"),
    ("Valorant", "https://playvalorant.com/en-us/", "shooter", "VALORANT"),
    ("Roblox", "https://www.roblox.com/", "social", "Roblox"),
]


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={**UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.geturl(), r.read(80000).decode("utf-8", "replace")


kept = []
print("== Steam API (is_free) ==")
for appid in STEAM_IDS:
    try:
        req = urllib.request.Request(
            f"https://store.steampowered.com/api/appdetails?appids={appid}",
            headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        info = (d.get(str(appid)) or {})
        data = info.get("data") or {}
        free = bool(data.get("is_free")) or (
            isinstance(data.get("price_overview"), dict)
            and data["price_overview"].get("final") == 0)
        name = data.get("name", "?")
        print(f"  [{'OK ' if (info.get('success') and free) else 'DROP'}] {appid} {name}")
        if info.get("success") and free:
            kept.append({"title": name, "url": f"https://store.steampowered.com/app/{appid}",
                         "price": "Free", "source": "SeedCatalog", "category": "games",
                         "description": "Permanently free-to-play title (seed catalog)."})
    except Exception as e:
        print(f"  [ERR ] {appid} {str(e)[:60]}")
    time.sleep(0.4)

print("== strony stale ==")
for title, url, category, marker in PAGES:
    try:
        status, final, body = get(url)
        ok = status == 200 and len(body) > 5000 and marker.lower() in body.lower()
        print(f"  [{'OK ' if ok else 'DROP'}] {title} ({len(body)}B)")
        if ok:
            kept.append({"title": title, "url": url, "price": "Free",
                         "source": "SeedCatalog", "category": category,
                         "description": "Permanently free-to-play title (seed catalog)."})
    except Exception as e:
        print(f"  [ERR ] {title} {str(e)[:60]}")
    time.sleep(0.5)

print(f"\nkept {len(kept)}")
print(json.dumps(kept, indent=1, ensure_ascii=False))
