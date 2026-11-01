"""Lokalne, gitignorowane muzeum okazów ataków złapanych przez sanityzer.

Append-only JSONL w .specimens/. Zapisuje WYŁĄCZNIE próbki zneutralizowane —
escapowane, ograniczone długością, nigdy nie wykonane i nigdy nie renderowane
jako HTML. To dowodownia, nie ścieżka wykonania. Nikt tego nie publikuje ani
nie wysyła — to lokalna kolekcja, żeby z czasem widzieć, jak zmieniają się
ataki.

Zero sieci, zero modelu: zestawienia liczymy deterministycznie (Counter).
"""
import hashlib
import json
import threading
import time
from collections import Counter
from pathlib import Path

DIR = Path(__file__).parent / ".specimens"
STORE = DIR / "specimens.jsonl"
MAX_SAMPLE = 2000
_lock = threading.Lock()

# Znaki sterujące poza tabulatorem i nową linią — do kosza, żeby okaz nie
# rozjeżdżał terminala ani nie udawał sekwencji terminalowych.
_CTRL = {c: None for c in range(0x20)}
_CTRL.pop(0x09, None)
_CTRL.pop(0x0a, None)


def _neutral(sample):
    return str(sample)[:MAX_SAMPLE].translate(_CTRL)


def record(source, field, detector, pattern, sample, match=""):
    """Dopisuje jeden okaz. sample = SUROWY tekst (z zachowanym trikiem)."""
    rec = {
        "ts": time.time(),
        "source": source or "",
        "field": field or "",
        "detector": detector or "",
        "pattern": pattern or "",
        "match": _neutral(match)[:200],
        "sha256": hashlib.sha256(
            str(sample).encode("utf-8", "replace")).hexdigest(),
        "sample": _neutral(sample),
    }
    with _lock:
        DIR.mkdir(exist_ok=True)
        with STORE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=True) + "\n")
    return rec


def record_findings(source, field, findings, sample):
    n = 0
    for fd in findings or []:
        record(source, field, fd.get("detector", ""), fd.get("pattern", ""),
               sample, fd.get("match", ""))
        n += 1
    return n


def _iter():
    if not STORE.exists():
        return
    with STORE.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def tail(limit=200):
    """Najnowsze okazy pierwsze."""
    items = list(_iter())
    return items[-limit:][::-1]


def stats():
    by_det, by_pat, by_src = Counter(), Counter(), Counter()
    total = 0
    for r in _iter():
        total += 1
        by_det[r.get("detector", "?")] += 1
        by_pat[r.get("pattern", "?")] += 1
        by_src[r.get("source", "?")] += 1
    return {"total": total,
            "by_detector": by_det.most_common(),
            "by_pattern": by_pat.most_common(),
            "by_source": by_src.most_common()}
