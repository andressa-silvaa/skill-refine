"""
Measure ESCO retrieval against the keyword heuristic for occupation and domain inference.

The v3 corpus is a free labelled evaluation set: every resume was generated from one ESCO
occupation, so `occupation.uri` is the ground-truth occupation and its ISCO-08 code gives the
ground-truth domain. Both providers are scored on the same rows, per language.

Query modes, because the query decides the number:
  title — targetPosition + experience positions + skills + courses (what production sends)
  full  — the whole rendered resume (what production sent before the occupation query existed)
  body  — summary + bullets + skills only, titles stripped. The generator writes the ESCO label
          into the job titles, so title/full are an optimistic upper bound; body is the honest
          floor, measuring recovery from the described work alone.

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/eval_domain_inference_esco.py
  ./backend/.venv/Scripts/python.exe ml/scripts/eval_domain_inference_esco.py --max-alt 0 4 --limit 200
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from apps.analysis.application.inference.resume_mapper import resume_to_text  # noqa: E402
from apps.analysis.application.inference.tasks.target_fit.domain_inference import (  # noqa: E402
    infer_domain_category,
)
from apps.analysis.application.inference.tasks.target_fit.esco_retrieval import (  # noqa: E402
    MAX_QUERY_CHARS,
    build_occupation_query,
    confidence_for,
    get_occupation_index,
    lang_key,
)
from apps.analysis.application.inference.tasks.target_fit.isco_domains import (  # noqa: E402
    domain_for_isco,
)

PROSE_PATH = REPO_ROOT / "ml" / "data" / "raw" / "resumes_v3" / "prose.jsonl"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = 5
QUERY_MODES = ("title", "full", "body")


def _load_rows(limit: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with PROSE_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            occupation = row.get("occupation") or {}
            if not occupation.get("uri") or not row.get("resume_data"):
                continue
            rows.append(row)
            if limit and len(rows) >= limit:
                break
    return rows


def _body_query(resume_data: dict[str, Any]) -> str:
    block = resume_data.get("data") or {}
    parts: list[str] = [str(block.get("summary") or "")]
    for experience in block.get("experiences") or []:
        for bullet in (experience or {}).get("description") or []:
            parts.append(str(bullet))
    skills = [str((s or {}).get("name") or "") for s in block.get("skills") or []]
    if skills:
        parts.append(", ".join(skills))
    return "\n".join(p for p in parts if p.strip())[:MAX_QUERY_CHARS]


def _query_for(mode: str, row: dict[str, Any]) -> str:
    resume_data = row["resume_data"]
    if mode == "title":
        return build_occupation_query(resume_data)
    if mode == "body":
        return _body_query(resume_data)
    language = row.get("language") or "pt-BR"
    return resume_to_text(resume_data, language=language).full_text[:MAX_QUERY_CHARS]


def _top_k_per_row(sims, row_to_occupation, top_k: int) -> list[list[tuple[int, float]]]:
    import numpy as np

    out: list[list[tuple[int, float]]] = []
    for row_sims in sims:
        order = np.argsort(-row_sims)
        taken: dict[int, float] = {}
        for position in order:
            occupation_id = int(row_to_occupation[position])
            if occupation_id in taken:
                continue
            taken[occupation_id] = float(row_sims[position])
            if len(taken) >= top_k:
                break
        out.append(list(taken.items()))
    return out


def _encode(model, texts: list[str]):
    import numpy as np

    emb = model.encode(
        texts,
        batch_size=64,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(emb, dtype=np.float32)


def _pct(hit: int, total: int) -> str:
    return f"{(100.0 * hit / total):5.1f}%" if total else "   n/a"


MARGIN_EDGES = (0.01, 0.02, 0.05, 0.10, 0.25)
COSINE_EDGES = (0.45, 0.55, 0.65, 0.75)


def _bucket(value: float, edges: tuple[float, ...]) -> str:
    for edge in edges:
        if value < edge:
            return f"<{edge:g}"
    return f">={edges[-1]:g}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="evaluate only the first N resumes")
    parser.add_argument("--max-alt", type=int, nargs="+", default=[0, 4], help="alt labels per occupation")
    parser.add_argument("--modes", nargs="+", default=list(QUERY_MODES), choices=QUERY_MODES)
    parser.add_argument("--skip-keyword", action="store_true", help="skip the keyword baseline")
    parser.add_argument("--json-out", default="", help="write the summary as JSON to this path")
    args = parser.parse_args()

    from sentence_transformers import SentenceTransformer

    rows = _load_rows(args.limit or None)
    if not rows:
        print(f"no rows in {PROSE_PATH}")
        return 1
    print(f"corpus: {len(rows)} resumes from {PROSE_PATH.name}")
    by_lang = Counter(lang_key(r.get("language")) for r in rows)
    print("languages: " + ", ".join(f"{k}={v}" for k, v in sorted(by_lang.items())))

    model = SentenceTransformer(MODEL_NAME)

    gold_domain = [domain_for_isco(r["occupation"].get("isco") or "") for r in rows]
    gold_uri = [r["occupation"]["uri"] for r in rows]
    langs = [lang_key(r.get("language")) for r in rows]

    summary: dict[str, Any] = {
        "corpus_rows": len(rows),
        "model": MODEL_NAME,
        "keyword": {},
        "embeddings": {},
    }

    for mode in [] if args.skip_keyword else ("full", "title"):
        print(f"\n== keyword heuristic (query={mode}) ==")
        keyword_hit = 0
        keyword_by_lang: dict[str, list[int]] = defaultdict(list)
        keyword_predictions = Counter()
        for i, row in enumerate(rows):
            found = infer_domain_category(_query_for(mode, row), lang=row.get("language"))
            predicted = str(found.get("domainCategory"))
            keyword_predictions[predicted] += 1
            ok = int(predicted == gold_domain[i])
            keyword_hit += ok
            keyword_by_lang[langs[i]].append(ok)
        print(f"domain accuracy: {_pct(keyword_hit, len(rows))}  ({keyword_hit}/{len(rows)})")
        for lang in sorted(keyword_by_lang):
            values = keyword_by_lang[lang]
            print(f"  {lang}: {_pct(sum(values), len(values))}  (n={len(values)})")
        print("  predicted mix: " + ", ".join(f"{k}={v}" for k, v in keyword_predictions.most_common(6)))
        summary["keyword"][mode] = {
            "domain_accuracy": keyword_hit / len(rows),
            "by_language": {k: sum(v) / len(v) for k, v in keyword_by_lang.items()},
            "predicted_mix": dict(keyword_predictions.most_common()),
        }

    for max_alt in args.max_alt:
        indexes = {}
        for lang in sorted(by_lang):
            indexes[lang] = get_occupation_index(model, lang, max_alt_labels=max_alt, model_name=MODEL_NAME)
            if indexes[lang] is None:
                print(f"index unavailable for {lang}")
                return 1

        for mode in args.modes:
            queries = [_query_for(mode, r) for r in rows]
            embeddings = _encode(model, queries)

            top1 = top5 = dom_hit = 0
            per_lang: dict[str, list[int]] = defaultdict(list)
            per_lang_occ: dict[str, list[int]] = defaultdict(list)
            by_confidence: dict[str, list[int]] = defaultdict(list)
            by_margin_bucket: dict[str, list[int]] = defaultdict(list)
            by_cosine_bucket: dict[str, list[int]] = defaultdict(list)
            cosines: list[float] = []
            margins: list[float] = []
            confusions = Counter()

            for lang in sorted(by_lang):
                index = indexes[lang]
                ids = [i for i, code in enumerate(langs) if code == lang]
                sims = embeddings[ids] @ index.matrix.T
                hits = _top_k_per_row(sims, index.row_to_occupation, TOP_K)
                for local, i in enumerate(ids):
                    ranked = hits[local]
                    uris = [index.occupations[occ_id].get("uri") for occ_id, _c in ranked]
                    best_cosine = ranked[0][1]
                    cosines.append(best_cosine)
                    is_top1 = int(uris[:1] == [gold_uri[i]])
                    top1 += is_top1
                    top5 += int(gold_uri[i] in uris)
                    per_lang_occ[lang].append(is_top1)

                    per_domain: dict[str, float] = {}
                    for occ_id, cosine in ranked:
                        domain = index.occupations[occ_id].get("domain") or "general"
                        per_domain[domain] = max(per_domain.get(domain, -1.0), cosine)
                    ordered = sorted(per_domain.items(), key=lambda kv: -kv[1])
                    predicted, best_score = ordered[0]
                    margin = best_score - (ordered[1][1] if len(ordered) > 1 else 0.0)
                    margins.append(margin)
                    ok = int(predicted == gold_domain[i])
                    dom_hit += ok
                    per_lang[lang].append(ok)
                    by_confidence[confidence_for(best_cosine, margin)].append(ok)
                    by_margin_bucket[_bucket(margin, MARGIN_EDGES)].append(ok)
                    by_cosine_bucket[_bucket(best_cosine, COSINE_EDGES)].append(ok)
                    if not ok:
                        confusions[f"{gold_domain[i]}->{predicted}"] += 1

            cosines.sort()
            margins.sort()
            n = len(cosines)
            print(f"\n== esco retrieval (alt={max_alt}, query={mode}) ==")
            print(f"occupation top-1: {_pct(top1, n)}   top-{TOP_K}: {_pct(top5, n)}")
            print(f"domain accuracy : {_pct(dom_hit, n)}  ({dom_hit}/{n})")
            for lang in sorted(per_lang):
                print(
                    f"  {lang}: domain {_pct(sum(per_lang[lang]), len(per_lang[lang]))}"
                    f"  occupation top-1 {_pct(sum(per_lang_occ[lang]), len(per_lang_occ[lang]))}"
                    f"  (n={len(per_lang[lang])})"
                )
            print(
                "  cosine p05/p50/p95: "
                f"{cosines[int(0.05 * (n - 1))]:.3f} / {cosines[int(0.5 * (n - 1))]:.3f} / {cosines[int(0.95 * (n - 1))]:.3f}"
                f"   margin p25/p50/p75: "
                f"{margins[int(0.25 * (n - 1))]:.3f} / {margins[int(0.5 * (n - 1))]:.3f} / {margins[int(0.75 * (n - 1))]:.3f}"
            )
            for bucket in ("high", "medium", "low"):
                values = by_confidence.get(bucket) or []
                if values:
                    print(f"  confidence {bucket:<6}: {_pct(sum(values), len(values))} (n={len(values)})")
            for name, table, edges in (
                ("margin", by_margin_bucket, MARGIN_EDGES),
                ("cosine", by_cosine_bucket, COSINE_EDGES),
            ):
                order = [f"<{e:g}" for e in edges] + [f">={edges[-1]:g}"]
                cells = [
                    f"{key}: {_pct(sum(table[key]), len(table[key]))} (n={len(table[key])})"
                    for key in order
                    if table.get(key)
                ]
                print(f"  by {name} -> " + " | ".join(cells))
            if confusions:
                print("  top confusions: " + ", ".join(f"{k} x{v}" for k, v in confusions.most_common(5)))

            summary["embeddings"][f"alt{max_alt}_{mode}"] = {
                "occupation_top1": top1 / n,
                f"occupation_top{TOP_K}": top5 / n,
                "domain_accuracy": dom_hit / n,
                "by_language": {k: sum(v) / len(v) for k, v in per_lang.items()},
                "cosine_median": cosines[int(0.5 * (n - 1))],
                "margin_median": margins[int(0.5 * (n - 1))],
                "confidence": {
                    k: {"accuracy": sum(v) / len(v), "n": len(v)} for k, v in by_confidence.items()
                },
            }

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
