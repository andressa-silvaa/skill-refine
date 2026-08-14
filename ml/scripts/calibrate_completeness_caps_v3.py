"""
Are the completeness caps justified? Measure before replacing them.

``quality_score_cap`` clamps the quality probe's answer to 40 when completeness reads ``insufficient``
and to 72 when it reads ``low``; a separate rule clamps to 58 when ``is_thin_student_or_intern_profile``
fires on a regex over job titles. Those three numbers were written by hand, and they cut the head that
carries 78% of the final score.

The stated reason for a cap is uncertainty: a resume with little content should not receive a
confident high score, because the model cannot really know. That is a testable claim, and this script
tests it rather than assuming it. Three questions, in order:

1. **Does the probe's confidence actually fall on sparse resumes?** If it does not, calibrated
   abstention has nothing to work with and the cap cannot be replaced by it — only removed or kept
   on other grounds.
2. **Is the probe less accurate there?** A cap on a bin where the head is accurate destroys correct
   answers.
3. **Does the cap even bind?** A cap that never fires is dead policy, and a cap that fires often on
   correct answers is a bug with a comment.

Known limit of this corpus, stated rather than worked around: it contains **no** resume that reads
``insufficient``, so the cap of 40 is unmeasurable here. Whatever this script concludes applies to
``low`` and to the thin-profile rule only.

Usage:
  ./backend/.venv/Scripts/python.exe ml/scripts/calibrate_completeness_caps_v3.py
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics
import sys
from datetime import date
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
for extra in (str(REPO_ROOT / "backend" / "src"), str(Path(__file__).resolve().parent)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["ANALYSIS_EMBEDDINGS_ENABLED"] = "true"
os.environ["ANALYSIS_QUALITY_PROBE_ENABLED"] = "true"

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

import label_seniority_llm_v3 as base  # noqa: E402

from apps.analysis.application.inference.completeness import (  # noqa: E402
    assess_completeness,
    quality_score_cap,
)
from apps.analysis.application.inference.config import get_config  # noqa: E402
from apps.analysis.application.inference.resume_mapper import resume_to_text  # noqa: E402
from apps.analysis.application.inference.resume_signals import (  # noqa: E402
    is_thin_student_or_intern_profile,
)
from apps.analysis.application.inference.tasks.quality.loader_quality_probe import (  # noqa: E402
    get_quality_probe_bundle,
)
from apps.analysis.application.inference.tasks.target_fit.loader_embeddings import (  # noqa: E402
    get_embeddings_model,
)
from apps.analysis.application.inference.text_probe import encode_for_bundle  # noqa: E402

REPORT_PATH = REPO_ROOT / "ml" / "reports" / "completeness_caps_v3.md"
RAW_DIR = REPO_ROOT / "ml" / "data" / "raw" / "resumes_v3"
THIN_CAP = 58


def load_quality_targets() -> dict[str, str]:
    targets: dict[str, str] = {}
    for name in ("specs.jsonl", "specs_b.jsonl", "specs_cal.jsonl", "specs_q.jsonl", "specs_q2.jsonl"):
        path = RAW_DIR / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            target = row.get("quality_target")
            if row.get("id") and target:
                targets[str(row["id"])] = str(target)
    return targets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--cache",
        default=str(REPO_ROOT / "ml" / "data" / "cache" / "caps_records.json"),
        help="scored rows are reused from here so the report can be reshaped without re-encoding",
    )
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    cache_path = Path(args.cache)
    if cache_path.exists() and not args.refresh and not args.limit:
        records = json.loads(cache_path.read_text(encoding="utf-8"))
        print(f"reusing {len(records)} scored rows from {cache_path.name} (--refresh to rescore)")
        return report(records)

    config = get_config(settings)
    encoder = get_embeddings_model(settings)
    bundle = get_quality_probe_bundle(config)
    if encoder is None or bundle is None:
        raise SystemExit("encoder or quality_probe unavailable")
    head = bundle["heads"]["level"]
    score_map = (bundle.get("_metadata") or {}).get("quality_level_to_score") or {}

    targets = load_quality_targets()
    rows = base.load_rows()
    if args.limit:
        rows = rows[: args.limit]
    print(f"scoring {len(rows)} resumes ...")

    records = []
    for index, row in enumerate(rows):
        resume_data = row.get("resume_data")
        if not isinstance(resume_data, dict):
            continue
        language = str(row.get("language") or "pt-BR")
        sections = resume_to_text(resume_data, language=language)
        completeness = assess_completeness(resume_data, sections)
        level = str(completeness.get("level") or "adequate")
        matrix = encode_for_bundle(bundle, encoder, sections.full_text, resume_data)
        probabilities = head.predict_proba(matrix)[0]
        predicted = str(head.classes_[int(np.argmax(probabilities))])
        ordered = np.sort(probabilities)[::-1]
        confidence = float(ordered[0])
        margin = float(ordered[0] - ordered[1])
        entropy = float(-np.sum(probabilities * np.log(np.clip(probabilities, 1e-12, None))))
        score = int(score_map.get(predicted, 55))
        records.append(
            {
                "id": row["id"],
                "level": level,
                "thin": bool(is_thin_student_or_intern_profile(resume_data)),
                "predicted": predicted,
                "confidence": confidence,
                "margin": margin,
                "entropy": entropy,
                "score": score,
                "cap": int(quality_score_cap(completeness)),
                "target": targets.get(str(row["id"])),
            }
        )
        if (index + 1) % 200 == 0:
            print(f"  {index + 1}/{len(rows)}")

    if not args.limit:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(records), encoding="utf-8")
        print(f"cached {len(records)} rows -> {cache_path}")
    report(records)


def report(records: list[dict]) -> None:
    out: list[str] = []
    out.append("# Completeness caps — are they justified?")
    out.append("")
    out.append(
        f"Generated {date.today().isoformat()} · {len(records)} resumes · quality head "
        "`quality_probe_v1`, confidence = max class probability."
    )
    out.append("")
    out.append(
        "**This corpus contains no resume that reads `insufficient`, so the cap of 40 is unmeasurable "
        "here.** Everything below concerns `low` (cap 72) and the thin-profile rule (cap 58)."
    )
    out.append("")

    def bucket_report(title: str, groups: dict[str, list[dict]]) -> None:
        out.append(f"## {title}")
        out.append("")
        out.append(
            "| grupo | n | confiança média | acurácia vs `quality_target` | n rotulado | cap | "
            "cap morde | score médio |"
        )
        out.append("|---|---|---|---|---|---|---|---|")
        for name, group in groups.items():
            if not group:
                continue
            confidence = statistics.mean(r["confidence"] for r in group)
            labelled = [r for r in group if r["target"]]
            accuracy = (
                sum(1 for r in labelled if r["predicted"] == r["target"]) / len(labelled)
                if labelled
                else float("nan")
            )
            cap = group[0]["cap"] if name != "thin" else THIN_CAP
            binds = sum(1 for r in group if r["score"] > cap)
            mean_score = statistics.mean(r["score"] for r in group)
            accuracy_text = "sem rótulo" if accuracy != accuracy else f"{accuracy:.1%}"
            out.append(
                f"| {name} | {len(group)} | {confidence:.3f} | {accuracy_text} | {len(labelled)} | "
                f"{cap} | {binds} ({100 * binds / len(group):.0f}%) | {mean_score:.1f} |"
            )
        out.append("")

    by_level = collections.OrderedDict()
    for name in ("adequate", "low", "insufficient"):
        by_level[name] = [r for r in records if r["level"] == name]
    bucket_report("Por nível de completude", by_level)

    bucket_report(
        "Regra de perfil raso",
        collections.OrderedDict(
            [
                ("thin", [r for r in records if r["thin"]]),
                ("not thin", [r for r in records if not r["thin"]]),
            ]
        ),
    )

    out.append("## A pergunta que decide a abstenção: a incerteza separa acerto de erro?")
    out.append("")
    out.append(
        "Abstenção calibrada só funciona se alguma medida de incerteza ordenar os acertos acima dos "
        "erros. Isso é testável em todos os currículos rotulados de uma vez, sem depender dos 16 de "
        "`low`. AUC 0,50 = a medida não sabe nada; 1,00 = separa perfeitamente."
    )
    out.append("")
    labelled = [r for r in records if r["target"]]
    if labelled:
        correct = np.array([r["predicted"] == r["target"] for r in labelled])
        out.append(f"n = {len(labelled)} rotulados · {int(correct.sum())} acertos, {int((~correct).sum())} erros")
        out.append("")
        out.append("| medida de incerteza | AUC (acerto vs erro) | média no acerto | média no erro |")
        out.append("|---|---|---|---|")
        for name, key, sign in (
            ("confiança (prob. máx.)", "confidence", 1.0),
            ("margem top-1 menos top-2", "margin", 1.0),
            ("entropia (invertida)", "entropy", -1.0),
        ):
            values = np.array([r[key] for r in labelled]) * sign
            positive, negative = values[correct], values[~correct]
            if len(positive) and len(negative):
                order = np.concatenate([positive, negative]).argsort()
                ranks = np.empty(len(order), dtype=float)
                ranks[order] = np.arange(1, len(order) + 1)
                auc = (ranks[: len(positive)].sum() - len(positive) * (len(positive) + 1) / 2) / (
                    len(positive) * len(negative)
                )
                out.append(
                    f"| {name} | **{auc:.3f}** | {positive.mean() * sign:.3f} | {negative.mean() * sign:.3f} |"
                )
        out.append("")

    if labelled:
        out.append("## Curva risco-cobertura pela margem")
        out.append("")
        out.append(
            "Abstendo dos currículos de menor margem, quanto sobe a acurácia no resto? A coluna "
            "`abstém` é a fração da base que deixaria de receber um número afirmado com confiança. "
            "É esta tabela, e não um valor escolhido a dedo, que fixa o ponto de operação."
        )
        out.append("")
        out.append("| abstém | corte de margem | n respondido | acurácia no respondido | erros restantes |")
        out.append("|---|---|---|---|---|")
        margins = np.array([r["margin"] for r in labelled])
        order = margins.argsort()
        for fraction in (0.0, 0.05, 0.10, 0.15, 0.20, 0.30):
            drop = int(round(fraction * len(labelled)))
            keep = order[drop:]
            if len(keep) < 20:
                continue
            kept_correct = correct[keep]
            cut = float(margins[order[drop]]) if drop else 0.0
            out.append(
                f"| {fraction:.0%} | {cut:.3f} | {len(keep)} | **{kept_correct.mean():.1%}** | "
                f"{int((~kept_correct).sum())} |"
            )
        out.append("")

    out.append("## O que o cap destrói quando morde")
    out.append("")
    capped = [
        r
        for r in records
        if r["target"] and (r["score"] > r["cap"] or (r["thin"] and r["score"] > THIN_CAP))
    ]
    if capped:
        correct = sum(1 for r in capped if r["predicted"] == r["target"])
        out.append(
            f"{len(capped)} currículos rotulados têm o score cortado por um cap. Nesses, a predição "
            f"da sonda estava **certa em {correct} ({100 * correct / len(capped):.0f}%)**: o corte "
            "não está removendo um erro do modelo, está removendo a resposta dele."
        )
    else:
        out.append("Nenhum currículo rotulado tem o score cortado — o cap não morde neste corpus.")
    out.append("")

    text = "\n".join(out)
    print(text)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text + "\n", encoding="utf-8")
    print(f"\nwrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
