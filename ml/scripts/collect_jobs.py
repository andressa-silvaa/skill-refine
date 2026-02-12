"""
Collect job postings for the ML pipeline. Primary: read from local public datasets (CSV/JSON).
Optional: scraping (disabled by default; use only if permitted and configured).
"""
from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path
from uuid import uuid4

# Scraping disabled by default; no external requests unless explicitly enabled
SCRAPING_ENABLED = False
RATE_LIMIT_SEC = 2.0

LANGUAGES = ("pt", "en", "es")
LANG_MAP = {"pt-BR": "pt", "pt": "pt", "en-US": "en", "en": "en", "es-ES": "es", "es": "es"}


def normalize_language(lang: str) -> str:
    return LANG_MAP.get(lang, "pt") if lang else "pt"


def read_jobs_from_json(path: Path, language: str, title_key: str = "title", desc_key: str = "description") -> list[dict]:
    """Read jobs from JSON array or JSONL. Each item: title, description (or mapped keys)."""
    jobs: list[dict] = []
    raw = path.read_text(encoding="utf-8").strip()
    lang_norm = normalize_language(language)
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "jobs" in data:
            items = data["jobs"]
        elif isinstance(data, dict) and "items" in data:
            items = data["items"]
        else:
            items = [data]
    except json.JSONDecodeError:
        items = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title = item.get(title_key) or item.get("title") or item.get("job_title") or ""
        desc = item.get(desc_key) or item.get("description") or item.get("body") or ""
        text = f"{title}\n{desc}".strip()
        if not text:
            continue
        jobs.append({
            "job_id": item.get("id") or item.get("job_id") or str(uuid4()),
            "language": lang_norm,
            "title": title,
            "description": desc,
            "job_text": text,
            "source": "public",
        })
    return jobs


def read_jobs_from_csv(
    path: Path,
    language: str,
    title_col: str = "title",
    desc_col: str = "description",
    delimiter: str = ",",
) -> list[dict]:
    """Read jobs from CSV. Headers must include title and description (or mapped)."""
    jobs: list[dict] = []
    lang_norm = normalize_language(language)
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        fieldnames = reader.fieldnames or []
        headers_lower = [h.strip().lower() for h in fieldnames]
        title_key = next((fn for fn, h in zip(fieldnames, headers_lower) if "title" in h or h == title_col.lower()), title_col)
        desc_key = next((fn for fn, h in zip(fieldnames, headers_lower) if "desc" in h or "description" in h or h == desc_col.lower()), desc_col)
        for row in reader:
            title = row.get(title_key) or row.get("title") or ""
            desc = row.get(desc_key) or row.get("description") or ""
            text = f"{title}\n{desc}".strip()
            if not text:
                continue
            jobs.append({
                "job_id": row.get("id") or row.get("job_id") or str(uuid4()),
                "language": lang_norm,
                "title": title,
                "description": desc,
                "job_text": text,
                "source": "public",
            })
    return jobs


def collect_from_local(source_dir: Path, language: str) -> list[dict]:
    """Collect jobs from local directory: JSON/JSONL/CSV."""
    all_jobs: list[dict] = []
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        suf = path.suffix.lower()
        try:
            if suf == ".json":
                all_jobs.extend(read_jobs_from_json(path, language))
            elif suf == ".jsonl":
                all_jobs.extend(read_jobs_from_json(path, language))
            elif suf == ".csv":
                all_jobs.extend(read_jobs_from_csv(path, language))
        except Exception as e:
            print(f"Warning: skip {path}: {e}", flush=True)
    return all_jobs


def collect_scraping(_language: str, _limit: int = 100) -> list[dict]:
    """Placeholder for scraping. Disabled by default; rate limit and robots must be respected."""
    if not SCRAPING_ENABLED:
        return []
    # If enabled: implement with requests + rate_limit + backoff; respect robots.txt
    time.sleep(RATE_LIMIT_SEC)
    return []


def run(source: Path | str, language: str, output: Path | None = None, limit: int | None = None) -> list[dict]:
    """
    Collect jobs. source: path to file or directory (local), or 'scraping' if enabled.
    Returns list of job dicts (job_id, language, title, description, job_text, source).
    """
    lang_norm = normalize_language(language)
    jobs: list[dict] = []
    src_str = str(source).lower()
    if src_str == "scraping":
        jobs = collect_scraping(lang_norm, limit or 100)
    else:
        path = Path(source)
        if path.is_file():
            if path.suffix.lower() == ".csv":
                jobs = read_jobs_from_csv(path, language)
            else:
                jobs = read_jobs_from_json(path, language)
        elif path.is_dir():
            jobs = collect_from_local(path, language)
        if limit:
            jobs = jobs[:limit]
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for j in jobs:
                f.write(json.dumps(j, ensure_ascii=False) + "\n")
    return jobs


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Collect job postings (local files or optional scraping)")
    p.add_argument("--source", type=str, required=True, help="Path to file/dir or 'scraping'")
    p.add_argument("--language", type=str, default="pt", choices=list(LANGUAGES) + ["pt-BR", "en-US", "es-ES"])
    p.add_argument("-o", "--output", type=Path, help="Output JSONL path")
    p.add_argument("--limit", type=int, help="Max jobs to collect")
    args = p.parse_args()
    jobs = run(args.source, args.language, output=args.output, limit=args.limit)
    print(f"Collected {len(jobs)} jobs", flush=True)
    if not args.output:
        print(json.dumps(jobs[:5], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
