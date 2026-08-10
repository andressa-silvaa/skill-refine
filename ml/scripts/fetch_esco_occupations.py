"""
Fetch the ESCO occupation vocabulary (pt/en/es labels + ISCO-08 code) for dataset generation.

ESCO is the EU multilingual occupation classification: free, ~3k occupations, each mapped to a
single ISCO-08 code, with preferred labels in 28 languages returned by one concept request.

Used ONLY offline to build the synthetic training corpus — the product never calls this API.
Occupation is a nuisance variable there: it is sampled uniformly and independently of the
seniority label, so its high cardinality stops any model from using domain as a shortcut.

Output: ml/data/reference/esco_occupations.jsonl
  {"uri", "isco", "isco_group", "labels": {"pt", "en", "es"}, "alt": {"pt", "en", "es"}}

Resumable: re-running skips URIs already present in the output file.

Usage (from repo root):
  python ml/scripts/fetch_esco_occupations.py
  python ml/scripts/fetch_esco_occupations.py --workers 8 --limit 200
"""
from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

BASE = "https://ec.europa.eu/esco/api"
SCHEME = "http://data.europa.eu/esco/concept-scheme/occupations"
LANGS = ("pt", "en", "es")
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "reference" / "esco_occupations.jsonl"

_print_lock = threading.Lock()


def _get(url: str, *, retries: int = 4) -> dict[str, Any]:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "skill-refine-ml/1.0"},
            )
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed after {retries} tries: {url}") from last


def _concept(uri: str, language: str = "en") -> dict[str, Any]:
    q = urllib.parse.urlencode({"uri": uri, "language": language})
    return _get(f"{BASE}/resource/concept?{q}")


def _links(node: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw = (node.get("_links") or {}).get(key) or []
    return raw if isinstance(raw, list) else [raw]


def collect_occupation_uris() -> list[tuple[str, str]]:
    """Walk the ISCO tree breadth-first, returning (occupation_uri, isco_group_title)."""
    q = urllib.parse.urlencode({"uri": SCHEME, "language": "en"})
    root = _get(f"{BASE}/resource/taxonomy?{q}")
    frontier = [(l["uri"], l.get("title") or "") for l in _links(root, "hasTopConcept")]

    seen_groups: set[str] = set()
    found: dict[str, str] = {}
    while frontier:
        nxt: list[tuple[str, str]] = []
        for uri, title in frontier:
            if uri in seen_groups:
                continue
            seen_groups.add(uri)
            try:
                node = _concept(uri)
            except RuntimeError:
                continue
            for occ in _links(node, "narrowerOccupation"):
                if occ.get("uri"):
                    found.setdefault(occ["uri"], title)
            for sub in _links(node, "narrowerConcept"):
                if sub.get("uri"):
                    nxt.append((sub["uri"], sub.get("title") or title))
        with _print_lock:
            print(f"  isco groups visited={len(seen_groups)} occupations found={len(found)}")
        frontier = nxt
    return sorted(found.items())


def fetch_one(uri: str, isco_group: str) -> dict[str, Any] | None:
    try:
        c = _concept(uri, "en")
    except RuntimeError:
        return None
    pref = c.get("preferredLabel") or {}
    alt = c.get("alternativeLabel") or {}
    labels = {lg: str(pref.get(lg) or "").strip() for lg in LANGS}
    if not all(labels.values()):
        return None
    alts = {}
    for lg in LANGS:
        vals = alt.get(lg) or []
        if isinstance(vals, str):
            vals = [vals]
        alts[lg] = [str(v).strip() for v in vals[:6] if str(v).strip()]
    code = str(c.get("code") or "")
    return {
        "uri": uri,
        "isco": code,
        "isco_group": isco_group,
        "labels": labels,
        "alt": alts,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    args = ap.parse_args()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    done: set[str] = set()
    if OUT_PATH.exists():
        for line in OUT_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["uri"])
                except (json.JSONDecodeError, KeyError):
                    continue
        print(f"resuming: {len(done)} already fetched")

    print("walking ISCO tree...")
    pairs = collect_occupation_uris()
    todo = [(u, g) for u, g in pairs if u not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"total occupations={len(pairs)} | to fetch={len(todo)}")

    written = 0
    with OUT_PATH.open("a", encoding="utf-8") as fh:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for row in pool.map(lambda p: fetch_one(*p), todo):
                if not row:
                    continue
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1
                if written % 100 == 0:
                    fh.flush()
                    with _print_lock:
                        print(f"  written={written}/{len(todo)}")

    print(f"done: +{written} rows -> {OUT_PATH}")


if __name__ == "__main__":
    main()
