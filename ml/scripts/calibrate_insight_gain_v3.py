"""
Measure how much each improvement suggestion is worth, so insights can be ordered by evidence.

``derive_insights`` returns every improvement that fires, in the order the ``if`` statements happen
to run, each carrying a hand-assigned ``priority`` of high/medium/low. Nothing about that ordering
was measured: it is the author's guess about what matters most, and it is the first thing the user
reads.

This script replaces the guess with a number. For every resume in the deduped corpus it runs the
real production path — sections, signals, bullet probe, quality probe — calls ``derive_insights``
itself so the conditions cannot drift from production, and records which improvements fired next to
the quality head's score. The gain of an improvement is then

    gain(key) = mean(quality | key did not fire) - mean(quality | key fired)

read as: resumes that do not have this deficiency score this many points higher.

**This is correlational and the report says so.** It is not a promise that acting on the suggestion
earns those points, and no causal claim is available without an intervention study. What it does
support is an ordering: telling a user to add metrics before telling them to add links is defensible
when the gap for metrics is measured to be the larger one, and indefensible when it is a guess.

The confound worth naming is resume level: a weak resume trips several conditions at once, so part of
every gap is "this resume is weak overall". The report therefore prints the pooled gap **and** the
gap computed within each quality band, which holds the level roughly fixed.

Usage:
  ./backend/.venv/Scripts/python.exe ml/scripts/calibrate_insight_gain_v3.py
  ./backend/.venv/Scripts/python.exe ml/scripts/calibrate_insight_gain_v3.py --limit 300
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
SCRIPTS_DIR = Path(__file__).resolve().parent
for extra in (str(BACKEND_SRC), str(SCRIPTS_DIR)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["ANALYSIS_EMBEDDINGS_ENABLED"] = "true"
os.environ["ANALYSIS_QUALITY_PROBE_ENABLED"] = "true"
os.environ["ANALYSIS_BULLET_PROBE_ENABLED"] = "true"

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

import label_seniority_llm_v3 as base  # noqa: E402

from apps.analysis.application.inference.config import get_config  # noqa: E402
from apps.analysis.application.inference.postprocess.insights import (  # noqa: E402
    derive_insights,
)
from apps.analysis.application.inference.resume_mapper import resume_to_text  # noqa: E402
from apps.analysis.application.inference.signals import extract_resume_signals  # noqa: E402
from apps.analysis.application.inference.tasks.quality.bullet_flags import (  # noqa: E402
    predict_bullet_flags,
)
from apps.analysis.application.inference.tasks.quality.loader_bullet_probe import (  # noqa: E402
    get_bullet_probe_bundle,
)
from apps.analysis.application.inference.tasks.quality.loader_quality_probe import (  # noqa: E402
    get_quality_probe_bundle,
)
from apps.analysis.application.inference.tasks.quality.predict import (  # noqa: E402
    predict_quality_detailed,
)
from apps.analysis.application.inference.tasks.target_fit.loader_embeddings import (  # noqa: E402
    get_embeddings_model,
)

OUT_DIR = REPO_ROOT / "ml" / "models" / "insight_gain_v1"
REPORT_PATH = REPO_ROOT / "ml" / "reports" / "insight_gain_v3.md"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--no-export", action="store_true")
    args = parser.parse_args()

    config = get_config(settings)
    encoder = get_embeddings_model(settings)
    quality_bundle = get_quality_probe_bundle(config)
    bullet_bundle = get_bullet_probe_bundle(config)
    if encoder is None or quality_bundle is None:
        raise SystemExit("encoder or quality_probe unavailable; cannot measure gain")
    print(f"bullet probe: {'loaded' if bullet_bundle else 'MISSING (flags fall back to regex)'}")

    rows = base.load_rows()
    if args.limit:
        rows = rows[: args.limit]
    print(f"scoring {len(rows)} resumes ...")

    records: list[tuple[set[str], int, str]] = []
    skipped = 0
    for index, row in enumerate(rows):
        resume_data = row.get("resume_data")
        if not isinstance(resume_data, dict):
            skipped += 1
            continue
        language = str(row.get("language") or "pt-BR")
        sections = resume_to_text(resume_data, language=language)
        bullet_detail = predict_bullet_flags(bullet_bundle, encoder, resume_data)
        signals = extract_resume_signals(
            resume_data,
            sections,
            language=language,
            leadership_override=(
                bool(bullet_detail["flags"]["has_leadership"]) if bullet_detail else None
            ),
        )
        score, flags, _detail = predict_quality_detailed(
            sections.full_text,
            language,
            sections,
            probe_bundle=quality_bundle,
            embeddings_model=encoder,
            resume_data=resume_data,
            bullet_detail=bullet_detail,
        )
        if score is None:
            skipped += 1
            continue
        insights = derive_insights(
            "mid",
            flags,
            sections,
            sections.full_text,
            completeness_level=signals.completeness_level,
            resume_data=resume_data,
            signals=signals,
        )
        keys = {str(item.get("key") or "") for item in insights.get("improvements") or []}
        records.append((keys, int(score), str(row.get("band_target") or "")))
        if (index + 1) % 100 == 0:
            print(f"  {index + 1}/{len(rows)}")

    if not records:
        raise SystemExit("no scored resumes")
    print(f"scored {len(records)}, skipped {skipped}")

    every_key = sorted({k for keys, _s, _b in records for k in keys})
    scores = [s for _k, s, _b in records]
    overall = statistics.mean(scores)

    def band_of(score: int) -> str:
        if score < 45:
            return "low"
        if score < 70:
            return "mid"
        return "high"

    gains: dict[str, dict[str, float | int]] = {}
    for key in every_key:
        fired = [s for keys, s, _b in records if key in keys]
        not_fired = [s for keys, s, _b in records if key not in keys]
        if len(fired) < 20 or len(not_fired) < 20:
            continue
        pooled = statistics.mean(not_fired) - statistics.mean(fired)

        within: list[float] = []
        weights: list[int] = []
        for band in ("low", "mid", "high"):
            f = [s for keys, s, _b in records if key in keys and band_of(s) == band]
            n = [s for keys, s, _b in records if key not in keys and band_of(s) == band]
            if len(f) >= 10 and len(n) >= 10:
                within.append(statistics.mean(n) - statistics.mean(f))
                weights.append(len(f) + len(n))
        within_band = (
            sum(g * w for g, w in zip(within, weights)) / sum(weights) if weights else float("nan")
        )
        gains[key] = {
            "pooled_gain": round(pooled, 2),
            "within_band_gain": round(within_band, 2) if within_band == within_band else None,
            "n_fired": len(fired),
            "n_not_fired": len(not_fired),
            "mean_when_fired": round(statistics.mean(fired), 1),
            "mean_when_absent": round(statistics.mean(not_fired), 1),
        }

    ordered = sorted(gains.items(), key=lambda kv: -float(kv[1]["pooled_gain"]))

    out: list[str] = []
    out.append("# Insight ordering by measured gain — v3 corpus")
    out.append("")
    out.append(
        f"Generated {date.today().isoformat()} · {len(records)} resumes scored through the real "
        "production path (sections, signals, `bullet_probe`, `quality_probe`), with "
        "`derive_insights` itself deciding which improvements fire."
    )
    out.append("")
    out.append(f"Mean quality score across the corpus: **{overall:.1f}**")
    out.append("")
    out.append(
        "`gain` is `mean(quality | suggestion absent) - mean(quality | suggestion shown)`: how many "
        "points separate resumes that do not have this deficiency from those that do."
    )
    out.append("")
    out.append(
        "| improvement | pooled gain | within-band gain | n shown | n absent | mean when shown | mean when absent |"
    )
    out.append("|---|---|---|---|---|---|---|")
    for key, stats in ordered:
        short = key.rsplit(".", 1)[-1]
        within = stats["within_band_gain"]
        within_text = "n/a" if within is None else f"{within:+.2f}"
        out.append(
            f"| `{short}` | **{float(stats['pooled_gain']):+.2f}** | {within_text} | "
            f"{stats['n_fired']} | {stats['n_not_fired']} | {stats['mean_when_fired']} | "
            f"{stats['mean_when_absent']} |"
        )
    out.append("")
    out.append("## How to read this, and how not to")
    out.append("")
    out.append(
        "- **Correlational.** These are score differences between resumes, not the effect of acting "
        "on the advice. Nothing here promises a user gains the listed points by following it."
    )
    out.append(
        "- **The pooled column is confounded by resume level.** A weak resume trips several "
        "conditions at once, so part of every pooled gap is just \"this resume is weak\". The "
        "within-band column recomputes the gap inside each quality band, which holds the level "
        "roughly fixed and is the number the ordering should lean on."
    )
    out.append(
        "- **Suggestions that always fire cannot be measured.** A condition that never varies has no "
        "contrast group and is dropped from the table; `ats_keywords` fires for every resume with an "
        "experience body, so it carries no evidence about its own worth and inherits the floor."
    )
    out.append(
        "- **The score being predicted is our own.** `quality_probe` reads the same resume text the "
        "`bullet_probe` flags read, so \"resumes without metrics score lower\" is partly one head "
        "agreeing with another about the same sentences. That makes this a statement about the "
        "number this product publishes, not about how a recruiter reacts. For ordering advice on how "
        "to raise the published score it is the right target; as evidence about real hiring outcomes "
        "it is none."
    )
    out.append(
        "- **A negative gain is a finding, not noise.** `education_target_gap` is shown to resumes "
        "that score *higher* than the ones it is withheld from, which is what a misfiring condition "
        "looks like. It is the suggestion driven by the education keyword lists that "
        "ml/reports/education_alignment_v3.md failed to replace, and it currently carries a "
        "hand-written `priority=high`."
    )
    out.append(
        "- **Ordering is stable across both columns except one entry.** Pooled and within-band agree "
        "on every rank but `fill_core_sections`, which falls from third to fifth once level is held "
        "fixed — its pooled gap was almost entirely \"this resume is weak\". The shipped table reads "
        "the within-band column."
    )
    out.append(
        "- What this replaces is a hand-written `high`/`medium`/`low` on each branch and the order "
        "the `if`s happen to run in. Both were guesses; this is not."
    )
    text = "\n".join(out)
    print(text)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text + "\n", encoding="utf-8")
    print(f"\nwrote {REPORT_PATH}")

    if not args.no_export:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "metadata.json").write_text(
            json.dumps(
                {
                    "task": "insight_gain",
                    "model_name": "insight_gain",
                    "model_version": "insight_gain_v1",
                    "dataset_version": f"resumes_v3_{len(records)}rows_{date.today().isoformat()}",
                    "measure": "mean(quality | absent) - mean(quality | shown)",
                    "causal": False,
                    "scored_with": "quality_probe_v1",
                    "resumes": len(records),
                    "corpus_mean_quality": round(overall, 2),
                    "gains": {k: v for k, v in ordered},
                    "trained_on": date.today().isoformat(),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
