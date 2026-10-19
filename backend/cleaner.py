"""Antysyf: fetch + sanitise untrusted external game pages.

The viewer (/view) serves third-party sites through here so visitors never
touch raw ad-/tracker-laden markup. Two layers:

1. SSRF guard (is_url_allowed) - only public http(s) hosts, ports 80/443,
   every redirect hop re-validated. The app binds 127.0.0.1, so an open
   fetch would otherwise reach the visitor's LAN.
2. clean_html - strips scripts, iframes, objects, forms, event handlers,
   tracking pixels and known ad/tracker domains; absolutises the rest.
"""
import ipaddress
import re
import socket
from urllib.parse import urlencode, urljoin, urlparse

ALLOWED_PORTS = {80, 443}
MAX_BYTES = 2 * 1024 * 1024

# Host substrings: ad/tracker delivery domains. These are matched against the
# HOSTNAME only, never the whole URL - matching the full URL deleted real
# content, because "beacon" and "pixel" are ordinary words in link slugs.
TRACKER_HOSTS = (
    "doubleclick.net", "googlesyndication.com", "google-analytics.com",
    "googletagmanager.com", "googleadservices.com", "facebook.net",
    "fbcdn.net", "hotjar.com", "crazyegg.com", "mixpanel.com",
    "segment.io", "newrelic.com", "scorecardresearch.com", "quantserve.com",
    "outbrain.com", "taboola.com", "criteo.com", "adservice.", "adsystem",
)
# Path forms that are unambiguous tracking endpoints. Deliberately NOT
# included: bare "/ads/" and "/track", because /ads/pricing is a real pricing
# page and /tracklist a real slug. Real ad URLs are already covered properly
# by the EasyList subscriptions, so the heuristic only needs the cases where
# a path IS the tracker.
TRACKER_PATH_PREFIXES = (
    "/pixel.", "/tracking-pixel", "/tracking/", "/telemetry/", "/beacon/",
    "/g/collect", "/stats/collect",
)
# Path tokens, only at a clean segment boundary. A dash is NOT a boundary:
# "/pixel-art-guide" is a guide, "/pixel.gif" is a pixel.
TRACKER_PATH_TOKENS = ("/pixel", "/beacon")

STRIP_TAGS = {"script", "iframe", "object", "embed", "applet",
              "meta", "link", "base"}
# Form controls stay: logins must work through the proxy. The server never
# stores submitted values - only Set-Cookie responses land in the host jar.
FORM_TAGS = {"form", "input", "button", "select", "textarea", "label",
             "option", "fieldset", "legend"}

_DANGEROUS_SCHEMES = ("javascript:", "data:", "vbscript:")
# Browsers strip ASCII tab/newline (and other C0 controls/space at the edges)
# from a URL BEFORE reading its scheme, so "java\tscript:alert(1)" and
# "\x01javascript:…" execute as javascript:. The old check compared the raw
# value with startswith, so those survived and /api/clean is same-origin -
# real script in the viewer. Normalise controls/space away BEFORE the test.
_CTRL_SPACE = re.compile(r"[\x00-\x20\x7f]")


def _dangerous_scheme(val):
    if not isinstance(val, str):
        return False
    return _CTRL_SPACE.sub("", val).lower().startswith(_DANGEROUS_SCHEMES)


def _is_global_ip(host):
    """True when host resolves exclusively to public routable addresses."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        ip = info[4][0]
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        if not addr.is_global:
            return False
    return True


def is_url_allowed(url, check_dns=True):
    """SSRF gate for the /api/clean proxy. Returns (ok, reason).

    check_dns=False skips local resolution (used when traffic goes through
    Tor/upstream: resolving locally would leak the hostname to the local
    resolver AND answer differently than the exit sees). Scheme/port/host
    syntax checks always apply.
    """
    try:
        parts = urlparse(url)
    except Exception:
        return False, "unparseable URL"
    if parts.scheme not in ("http", "https"):
        return False, "only http(s) allowed"
    if not parts.hostname:
        return False, "missing host"
    port = parts.port or (443 if parts.scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        return False, "port not allowed"
    if check_dns and not _is_global_ip(parts.hostname):
        return False, "non-public host"
    return True, ""


def _is_tracker(url):
    """True for known tracking endpoints, matched on the right component.

    Previously every entry was a substring test over the whole URL, so
    /pixel-art-guide, /beacon-training.html and /ads/pricing were treated as
    trackers and tag.decompose() deleted the element - including real <a>
    links, because src fell back to href."""
    if not url:
        return False
    from urllib.parse import urlparse
    try:
        parts = urlparse(url)
    except Exception:
        return False
    host = (parts.hostname or "").lower()
    if any(t in host for t in TRACKER_HOSTS):
        return True
    path = (parts.path or "").lower()
    if any(path.startswith(p) for p in TRACKER_PATH_PREFIXES):
        return True
    for tok in TRACKER_PATH_TOKENS:
        # boundary before and after the token, so /pixel-art is fine but
        # /px/pixel.gif and /img/pixel/track are not
        i = path.find(tok)
        while i != -1:
            before_ok = i == 0 or path[i - 1] in "/.-_"
            end = i + len(tok)
            after_ok = end >= len(path) or path[end] in "/._?&"
            if before_ok and after_ok:
                return True
            i = path.find(tok, i + 1)
    return False


def _filter_check(flt, page_url, resource_url, res_type):
    """(blocked, rule) via custom engine first, then subscriptions."""
    if not flt or not resource_url:
        return False, None
    custom = flt.get("custom")
    if custom is not None:
        blocked, rule = custom.check(page_url, resource_url, res_type)
        if blocked:
            return True, rule
    eng = flt.get("engine")
    if eng is not None:
        return eng.check(page_url, resource_url, res_type,
                         enabled=flt.get("enabled"))
    return False, None


def clean_html(html, base_url, flt=None):
    """Return (clean_html, removed_count, blocked_count). Pure function,
    fully unit-tested.

    flt: optional {"engine", "custom", "enabled", "log"} - when given,
    subresource URLs are additionally judged by the filter engine and every
    block is recorded in the shared filter log with the exact rule + list.
    """
    from bs4 import BeautifulSoup
    from filterlists import elog

    soup = BeautifulSoup(html, "html.parser")
    removed = 0
    filtered = 0

    for tag in soup.find_all(True):
        if not tag.name:
            continue
        name = tag.name.lower()
        if name in STRIP_TAGS:
            # Keep stylesheets and the document charset; drop the rest
            # (preload-as-script, refresh-redirects, icons are harmless but
            # useless through the proxy).
            if name == "link":
                rel = " ".join(tag.get("rel", [])).lower()
                if tag.get("rel") == ["stylesheet"] or "stylesheet" in rel:
                    href = tag.get("href", "")
                    if href and not _dangerous_scheme(href):
                        tag["href"] = urljoin(base_url, href)
                        # NO continue: stylesheets must still face the tracker
                        # heuristic and the filter engine. Skipping them meant
                        # the "link": "stylesheet" mapping below was dead code
                        # and an ad host in a <link> survived untouched.
                        if _is_tracker(tag["href"]):
                            tag.decompose()
                            removed += 1
                            continue
                        blocked, _rule = _filter_check(
                            flt, base_url, tag["href"], "stylesheet")
                        if blocked:
                            tag.decompose()
                            removed += 1
                            filtered += 1
                        continue
                tag.decompose()
                removed += 1
                continue
            if name == "meta":
                if (tag.get("charset") or tag.get("http-equiv", "").lower() == "content-type"):
                    continue
                tag.decompose()
                removed += 1
                continue
            tag.decompose()
            removed += 1
            continue

        # Event handler attributes (onclick=…) execute - strip them all.
        for attr in [a for a in tag.attrs if a.lower().startswith("on")]:
            del tag.attrs[attr]
            removed += 1

        # formaction would bypass the rewritten form action below.
        if tag.has_attr("formaction"):
            del tag.attrs["formaction"]
            removed += 1

        if name == "form":
            action = tag.get("action", "") or ""
            # Percent-encode the proxied target. Concatenation lost every
            # "?" inside the action, so checkout?step=2&lang=en#pay became
            # url=...checkout?step=2 with "lang=en" and the fragment
            # orphaned onto our own endpoint.
            target = urljoin(base_url, action) if action else base_url
            tag["action"] = "/api/clean?" + urlencode({"url": target})
            if not tag.get("method"):
                tag["method"] = "get"

        # Dangerous URL schemes in any URL-bearing attribute. style is in
        # the list because url(javascript:…) / url(data:…) inside an inline
        # style is the same hazard as a javascript: href. xlink:href and
        # srcset were missing: <svg><a xlink:href="javascript:…">> survived
        # sanitising, and /api/clean is same-origin, so that is real script.
        for attr in ("href", "src", "action", "cite", "data", "poster", "style",
                     "xlink:href", "srcset", "background", "dynsrc", "lowsrc",
                     "formaction", "srcdoc", "ping"):
            val = tag.get(attr)
            if isinstance(val, str):
                low = val.strip().lower()
                if attr == "style":
                    flat = _CTRL_SPACE.sub("", low)
                    if "javascript:" in flat or "expression(" in flat:
                        del tag.attrs[attr]
                        removed += 1
                elif attr == "srcset":
                    # A srcset is a list of URLs: absolutise each, and drop the
                    # whole attribute if ANY candidate is a known tracker.
                    cands = [p.strip() for p in val.split(",") if p.strip()]
                    if not cands:
                        del tag.attrs[attr]
                        removed += 1
                    else:
                        rebuilt = []
                        for part in cands:
                            bits = part.split(" ")
                            low_u = bits[0].strip().lower()
                            if _dangerous_scheme(bits[0]):
                                continue
                            u = urljoin(base_url, bits[0])
                            desc = (" " + bits[1]) if len(bits) > 1 else ""
                            if not _is_tracker(u):
                                rebuilt.append(u + desc)
                        if rebuilt:
                            tag[attr] = ", ".join(rebuilt)
                        else:
                            del tag.attrs[attr]
                            removed += 1
                elif _dangerous_scheme(val):
                    del tag.attrs[attr]
                    removed += 1
                elif attr in ("href", "src") and val and not low.startswith(("#", "mailto:")):
                    tag[attr] = urljoin(base_url, val)

        # Tracking pixels and ad hosts (legacy heuristics).
        src = tag.get("src", "") or tag.get("href", "")
        if src and _is_tracker(src):
            tag.decompose()
            removed += 1
            continue
        if tag.name == "img":
            try:
                w, h = int(tag.get("width", 0) or 0), int(tag.get("height", 0) or 0)
            except (ValueError, TypeError):
                w = h = 0
            style = (tag.get("style") or "").replace(" ", "")
            if (w == 1 and h == 1) or "1px" in style or "display:none" in style:
                tag.decompose()
                removed += 1
                continue

        # Subscription filter lists (uBlock-style): judge subresource loads.
        # Anchors are deliberately NOT removed - clicking stays the user's
        # choice (and outbound routes it through the viewer anyway).
        res_type = {"img": "image", "source": "media", "video": "media",
                    "audio": "media", "link": "stylesheet"}.get(tag.name, "other")
        for attr in ("src", "poster"):
            val = tag.get(attr)
            if isinstance(val, str) and val.startswith(("http://", "https://")):
                blocked, rule = _filter_check(flt, base_url, val, res_type)
                if blocked:
                    if flt.get("log", True):
                        from filterlists import elog as _elog
                        _elog.add(base_url, val, rule, "blocked-load")
                    tag.decompose()
                    removed += 1
                    filtered += 1
                    break

    # <base> makes every relative link/image work inside the iframe.
    if soup.head is not None:
        base_tag = soup.new_tag("base", href=base_url)
        soup.head.insert(0, base_tag)

    return str(soup), removed, filtered
