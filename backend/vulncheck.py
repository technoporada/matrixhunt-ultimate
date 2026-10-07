"""Dependency audit + exploit feed. Manual trigger only - never background.

Two keyless sources:
- OSV (api.osv.dev): per-package known CVEs for our exact venv versions.
- CISA KEV catalog: what is ACTIVELY exploited in the wild right now.
Results are cached (data/vulncheck.json, backend/.kev.json) so re-reading
costs zero third-party traffic.
"""
import json
import time
from pathlib import Path

HERE = Path(__file__).parent
KEV_CACHE = HERE / ".kev.json"
AUDIT_CACHE = HERE.parent / "data" / "vulncheck.json"
KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
OSV_URL = "https://api.osv.dev/v1/querybatch"
KEV_TTL = 24 * 3600


def installed_packages():
    """Name -> version for project deps present in this venv."""
    from importlib.metadata import version, PackageNotFoundError
    out = {}
    for name in ("fastapi", "uvicorn", "starlette", "anyio", "aiohttp",
                 "beautifulsoup4", "sqlalchemy", "requests", "itsdangerous",
                 "PySocks", "cryptography", "jinja2"):
        try:
            out[name] = version(name)
        except PackageNotFoundError:
            continue
    return out


def _post_json(url, payload, timeout=30):
    import requests as _requests
    r = _requests.post(url, json=payload, timeout=timeout,
                       headers={"User-Agent": "MatrixHunt/2.0 (vulncheck)",
                                "Content-Type": "application/json"})
    r.raise_for_status()
    return r.json()


def check_osv(packages):
    """Batch OSV query. Returns {name: [vuln...]}. Network errors -> {}."""
    names = list(packages)
    if not names:
        return {}
    try:
        data = _post_json(OSV_URL, {"queries": [
            {"package": {"name": n, "ecosystem": "PyPI"}, "version": packages[n]}
            for n in names]})
    except Exception as e:
        return {"_error": str(e)[:120]}
    out = {}
    for name, res in zip(names, data.get("results", [])):
        vulns = []
        for v in res.get("vulns", []):
            sev = ""
            for s in v.get("severity", []) or []:
                if s.get("type", "").endswith("CVSS_V3"):
                    sev = s.get("score", "")
                    break
            vulns.append({"id": v.get("id"), "summary": (v.get("summary") or "")[:200],
                          "severity": sev,
                          "fixed": ",".join(
                              e.get("fixed", "") for e in
                              (v.get("affected") or [{}])[0].get("ranges", [{}])[0].get("events", [])
                              if e.get("fixed")) or "see advisory",
                          "details": (v.get("details") or "")[:400]})
        out[name] = vulns
    return out


def _kev_catalog():
    try:
        if KEV_CACHE.exists() and time.time() - KEV_CACHE.stat().st_mtime < KEV_TTL:
            return json.loads(KEV_CACHE.read_text())
    except Exception:
        pass
    import requests as _requests
    r = _requests.get(KEV_URL, timeout=60,
                      headers={"User-Agent": "MatrixHunt/2.0 (vulncheck)"})
    r.raise_for_status()
    data = r.json()
    try:
        KEV_CACHE.write_text(json.dumps(data))
        KEV_CACHE.chmod(0o600)
    except OSError:
        pass
    return data


def kev_search(query, limit=30):
    """Actively-exploited CVEs matching vendor/product/name. Empty query -> newest."""
    try:
        vulns = _kev_catalog().get("vulnerabilities", [])
    except Exception as e:
        return {"error": str(e)[:120], "items": []}
    q = (query or "").lower().strip()
    items = []
    for v in vulns:
        hay = " ".join([v.get("cveID", ""), v.get("vendorProject", ""),
                        v.get("product", ""), v.get("vulnerabilityName", "")]).lower()
        if not q or q in hay:
            items.append({"cve": v.get("cveID"), "vendor": v.get("vendorProject"),
                          "product": v.get("product"), "name": v.get("vulnerabilityName"),
                          "date_added": v.get("dateAdded"),
                          "ransomware": v.get("knownRansomwareCampaignUse")})
    items.sort(key=lambda x: x.get("date_added") or "", reverse=True)
    return {"count": len(items), "items": items[:limit]}


def run_audit():
    """Full audit, cached to data/vulncheck.json. Returns the report.

    An OSV network failure used to land in the report as a "_error" key, and
    `total` summed everything else to 0, so the dashboard happily rendered
    "0 vulnerabilities" while the audit had never run. The report now carries
    a completeness flag and a non-empty ok:false, and the endpoint refuses to
    cache a failed run as if it were a clean bill of health.
    """
    pkgs = installed_packages()
    osv = check_osv(pkgs)
    errors = {k: v for k, v in osv.items() if k.startswith("_")}
    total = sum(len(v) for k, v in osv.items() if not k.startswith("_"))
    ok = not errors
    report = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "packages": pkgs, "vulns": osv, "total": total,
              "ok": ok, "errors": errors}
    # Do not overwrite a good cache with a failed run.
    if ok:
        try:
            AUDIT_CACHE.write_text(json.dumps(report, indent=1))
        except OSError:
            pass
    return report


def cached_audit():
    try:
        report = json.loads(AUDIT_CACHE.read_text())
    except Exception:
        # No cache at all: that is "never audited", not "0 vulnerabilities".
        return {"checked_at": None, "packages": {}, "vulns": {}, "total": 0,
                "ok": False, "errors": {"_cache": "no audit has ever been run"}}
    report.setdefault("ok", True)
    report.setdefault("errors", {})
    return report
