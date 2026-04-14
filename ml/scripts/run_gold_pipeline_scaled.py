#!/usr/bin/env python3
"""
Pipeline gold em escala: seed + batch iterativo, export v1.1, validate, ML, A/B,
ajuste opcional de thresholds, relatório único `gold_run_summary.md`.

Um comando (raiz do repo). Em **PowerShell** use uma linha só, ou continue com **backtick** `` ` `` (não use `^`, que é só cmd.exe).

  # PowerShell — uma linha
  python ml/scripts/run_gold_pipeline_scaled.py --user-email dev@local.seed.invalid --target-done 800 --min-dataset-rows 500 --min-classes 3 --seed-count 800 --batch-limit 800 --concurrency 8 --only-missing --sync

  # Bash — barra invertida no fim da linha
  python ml/scripts/run_gold_pipeline_scaled.py \\
    --user-email dev@local.seed.invalid \\
    --target-done 800 --min-dataset-rows 500 --min-classes 3 \\
    --seed-count 800 --batch-limit 800 --concurrency 8 --only-missing --sync

HF/torch podem falhar no Windows; o batch usa o worker Django (policy + heurísticas)
e o treino é signals_ml (sklearn), sem depender de torch.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOW_LABELS = frozenset({"intern", "junior", "mid", "senior"})
EXPORT_CAP = 50_000
DEFAULT_THRESHOLDS: dict[str, Any] = {
    "senior_prob_threshold": 0.70,
    "senior_min_total_months": 60,
    "senior_min_experiences": 2,
    "senior_min_bullets": 6,
}


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> int:
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=str(cwd), env=env or os.environ.copy())
    return int(r.returncode)


def _count_done_for_user(manage_py: Path, py: str, email: str, env: dict[str, str]) -> int:
    code = (
        "from apps.analysis.models import ResumeAnalysis, AnalysisStatus; "
        "from apps.accounts.infrastructure.models import User; "
        f"u = User.objects.filter(email__iexact={email!r}, deleted_at__isnull=True).first(); "
        "print(ResumeAnalysis.objects.filter(user_id=u.id, status=AnalysisStatus.DONE).count() if u else 0)"
    )
    r = subprocess.run(
        [py, str(manage_py), "shell", "-c", code],
        cwd=str(manage_py.parent),
        env=env,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return -1
    try:
        return int((r.stdout or "").strip().splitlines()[-1].strip())
    except (ValueError, IndexError):
        return -1


def _analyze_jsonl(path: Path) -> tuple[int, Counter[str], int]:
    dist: Counter[str] = Counter()
    n = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            n += 1
            labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
            lab = str(labels.get("seniority_label") or "").strip()
            dist[lab or "(empty)"] += 1
    classes = sum(1 for k, v in dist.items() if k in ALLOW_LABELS and v > 0)
    return n, dist, classes


def _parse_ab_senior_shares(ab_md: Path) -> tuple[str | None, str | None]:
    if not ab_md.is_file():
        return None, None
    before = after = None
    for line in ab_md.read_text(encoding="utf-8").splitlines():
        if "`senior` % before" in line and "rule-only" in line:
            before = line.strip().lstrip("- ").strip()
        if "`senior` % after" in line and "signals_ml" in line:
            after = line.strip().lstrip("- ").strip()
    return before, after


def _parse_phantom_after(ab_md: Path) -> int | None:
    if not ab_md.is_file():
        return None
    text = ab_md.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "still violating evidence" in line and "after signals_ml" in line:
            m = re.search(r"\*\*: (\d+)\s*$", line)
            if m:
                return int(m.group(1))
        if "still violating evidence**:" in line:
            m = re.search(r"evidence\*\*: (\d+)", line)
            if m:
                return int(m.group(1))
    return None


def _bump_thresholds(base: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    prob = float(out.get("senior_prob_threshold", 0.70)) + 0.05
    out["senior_prob_threshold"] = min(0.85, round(prob, 2))
    bullets = int(out.get("senior_min_bullets", 6)) + 2
    out["senior_min_bullets"] = min(12, bullets)
    return out


def _write_threshold_json(path: Path, thr: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"inference_thresholds": thr}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class RunState:
    started_at: str = ""
    iterations_used: int = 0
    seed_counts_per_iter: list[int] = field(default_factory=list)
    batch_limits_per_iter: list[int] = field(default_factory=list)
    done_count: int = 0
    dataset_rows: int = 0
    label_dist: Counter[str] = field(default_factory=Counter)
    n_classes: int = 0
    dataset_version: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    criteria_met: bool = False
    ab_phantom_after_pass1: int | None = None
    ab_phantom_after_pass2: int | None = None
    ab_senior_before: str | None = None
    ab_senior_after: str | None = None
    threshold_bump_applied: bool = False
    threshold_recommendations: list[str] = field(default_factory=list)


def _write_gold_summary(
    path: Path,
    *,
    args: argparse.Namespace,
    state: RunState,
    eval_md: Path,
    ab_md: Path,
    evolution_md: Path,
) -> None:
    lines = [
        "# Gold pipeline — resumo da execução (TCC)",
        "",
        f"- **Gerado em**: {state.started_at}",
        f"- **user-email**: `{args.user_email}`",
        f"- **iterações (seed/batch)**: {state.iterations_used}",
        f"- **seed por iteração**: {state.seed_counts_per_iter}",
        f"- **batch_limit por iteração**: {state.batch_limits_per_iter}",
        f"- **target-done (meta)**: {args.target_done}",
        f"- **Análises DONE (utilizador seed)**: {state.done_count}",
        "",
        "## Dataset exportado (v1.1)",
        "",
        f"- **linhas (JSONL)**: {state.dataset_rows}",
        f"- **classes presentes (intern/junior/mid/senior)**: {state.n_classes}",
        "",
        "### Distribuição `labels.seniority_label`",
        "",
    ]
    for k, v in sorted(state.label_dist.items(), key=lambda x: (-x[1], x[0])):
        pct = 100.0 * v / state.dataset_rows if state.dataset_rows else 0.0
        lines.append(f"- `{k}`: {v} ({pct:.1f}%)")
    lines.extend(
        [
            "",
            f"- **dataset_version** (split): `{state.dataset_version}`",
            f"- **Critérios (≥{args.min_dataset_rows} linhas, ≥{args.min_classes} classes)**: "
            f"{'OK' if state.criteria_met else 'NÃO ATENDIDOS'}",
            "",
            "## Métricas do modelo (test holdout)",
            "",
        ]
    )
    acc = state.metrics.get("accuracy")
    f1 = state.metrics.get("f1_macro")
    lines.append(f"- **accuracy**: {acc}")
    lines.append(f"- **f1_macro**: {f1}")
    cm = state.metrics.get("confusion_matrix")
    labels = state.metrics.get("labels")
    if cm is not None and labels is not None:
        lines.extend(["", "### Matriz de confusão (JSON)", "", "```json", json.dumps(cm, indent=2), "```", ""])
    lines.append(f"- **Relatório detalhado**: `{eval_md.as_posix()}`")
    lines.extend(
        [
            "",
            "## A/B low-confidence (signals_ml vs policy)",
            "",
            f"- **Relatório**: `{ab_md.as_posix()}`",
        ]
    )
    if state.ab_senior_before:
        lines.append(f"- **A/B (share `senior`) — antes (só regras)**: {state.ab_senior_before}")
    if state.ab_senior_after:
        lines.append(f"- **A/B (share `senior`) — depois (signals_ml + gates)**: {state.ab_senior_after}")
    lines.append(f"- **phantom `senior` após ML (passo 1)**: {state.ab_phantom_after_pass1}")
    if state.threshold_bump_applied:
        lines.append(f"- **phantom após thresholds ajustados (passo 2)**: {state.ab_phantom_after_pass2}")
    lines.extend(
        [
            "",
            "### Thresholds / policy",
            "",
        ]
    )
    if state.threshold_recommendations:
        for t in state.threshold_recommendations:
            lines.append(f"- {t}")
    else:
        lines.append("- Nenhuma recomendação extra (phantom baixo ou não detetado).")
    lines.extend(
        [
            "",
            "## Evolução do dataset",
            "",
            f"- **Log append**: `{evolution_md.as_posix()}`",
            "",
            "---",
            "",
            "_Reprodutível com_: `python ml/scripts/run_gold_pipeline_scaled.py` (ver `ml/README.md`).",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {path}", flush=True)


def main() -> int:
    root = _root()
    backend = root / "backend"
    py = sys.executable
    manage = backend / "manage.py"
    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    p = argparse.ArgumentParser(description="Gold pipeline scaled: seed, batch, export, train, A/B, summary.")
    p.add_argument("--user-email", required=True, help="Utilizador seed (get_or_create em seed_resumes).")
    p.add_argument("--target-done", type=int, default=800)
    p.add_argument("--min-dataset-rows", type=int, default=500)
    p.add_argument("--min-classes", type=int, default=3)
    p.add_argument("--seed-count", type=int, default=800)
    p.add_argument("--batch-limit", type=int, default=800)
    p.add_argument("--seed-increment", type=int, default=400, help="Soma a seed/batch por iteração extra.")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--sleep-ms", type=int, default=30)
    p.add_argument("--only-missing", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--sync", action="store_true", help="batch_run_analysis --sync (sem Celery).")
    p.add_argument("--since", default="180d")
    p.add_argument("--max-iterations", type=int, default=3)
    p.add_argument("--out-model-version", default="seniority_signals_v1", dest="out_model_version")
    p.add_argument("--profiles", default="balanced")
    p.add_argument("--resume-tag", default="seed_synthetic")
    p.add_argument("--seed-base", type=int, default=42)
    p.add_argument("--split-seed", type=int, default=42)
    p.add_argument(
        "--continue-on-short-dataset",
        action="store_true",
        help="Seguir com train/eval mesmo se min_dataset_rows/min_classes não forem atingidos após max_iterations.",
    )
    args = p.parse_args()

    jsonl_path = root / "ml/data/processed/seniority_from_db.jsonl"
    low_path = root / "ml/data/processed/low_confidence.jsonl"
    split_dir = root / "ml/data/splits" / args.out_model_version
    model_dir = root / "ml/models" / args.out_model_version
    eval_md = root / "ml/training/reports/eval_seniority.md"
    metrics_json = model_dir / "test_metrics.json"
    ab_md = root / "ml/training/reports/ab_low_confidence_report.md"
    evolution_md = root / "ml/training/reports/dataset_evolution.md"
    summary_md = root / "ml/training/reports/gold_run_summary.md"
    thresh_json = root / "ml/training/reports/threshold_gold_scaled_bump.json"

    state = RunState(started_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    rc = _run([py, str(manage), "migrate", "--noinput"], cwd=backend, env=env)
    if rc:
        return rc

    seed_cur = max(1, args.seed_count)
    batch_cur = max(1, args.batch_limit)

    for it in range(args.max_iterations):
        state.iterations_used = it + 1
        state.seed_counts_per_iter.append(seed_cur)
        state.batch_limits_per_iter.append(batch_cur)

        rc = _run(
            [
                py,
                str(manage),
                "seed_resumes",
                "--user-email",
                args.user_email,
                "--count",
                str(seed_cur),
                "--seed",
                str(args.seed_base),
                "--profiles",
                args.profiles,
                "--tag",
                args.resume_tag,
            ],
            cwd=backend,
            env=env,
        )
        if rc:
            return rc

        batch_cmd = [
            py,
            str(manage),
            "batch_run_analysis",
            "--user-email",
            args.user_email,
            "--limit",
            str(batch_cur),
            "--concurrency",
            str(args.concurrency),
            "--sleep-ms",
            str(args.sleep_ms),
            "--resume-tag",
            args.resume_tag,
        ]
        if args.only_missing:
            batch_cmd.append("--only-missing")
        if args.sync:
            batch_cmd.append("--sync")
        rc = _run(batch_cmd, cwd=backend, env=env)
        if rc:
            return rc

        rc = _run(
            [
                py,
                str(manage),
                "export_seniority_dataset",
                "--out",
                str(jsonl_path),
                "--schema-version",
                "1.1",
                "--limit",
                str(EXPORT_CAP),
                "--since",
                args.since,
            ],
            cwd=backend,
            env=env,
        )
        if rc:
            return rc

        rc = _run(
            [
                py,
                str(manage),
                "export_low_confidence_cases",
                "--out",
                str(low_path),
                "--schema-version",
                "1.1",
                "--limit",
                str(EXPORT_CAP),
            ],
            cwd=backend,
            env=env,
        )
        if rc:
            return rc

        rc = _run(
            [
                py,
                str(root / "ml/training/src/validate_dataset.py"),
                "--in",
                str(jsonl_path),
                "--report",
                str(root / "ml/training/reports/dataset_report.md"),
            ],
            cwd=root,
        )
        if rc:
            print("validate_dataset reported issues; aborting.", file=sys.stderr)
            return rc

        n_rows, dist, n_cls = _analyze_jsonl(jsonl_path)
        done_n = _count_done_for_user(manage, py, args.user_email, env)
        state.dataset_rows = n_rows
        state.label_dist = dist
        state.n_classes = n_cls
        state.done_count = done_n

        need_rows = n_rows < args.min_dataset_rows
        need_cls = n_cls < args.min_classes
        need_done = done_n >= 0 and done_n < args.target_done
        satisfied = not need_rows and not need_cls
        done_ok = done_n < 0 or not need_done

        if satisfied and done_ok:
            break
        if it == args.max_iterations - 1:
            break
        seed_cur = min(50_000, seed_cur + args.seed_increment)
        batch_cur = min(50_000, batch_cur + args.seed_increment)

    state.criteria_met = (
        state.dataset_rows >= args.min_dataset_rows and state.n_classes >= args.min_classes
    )
    if not state.criteria_met and not args.continue_on_short_dataset:
        _write_gold_summary(
            summary_md,
            args=args,
            state=state,
            eval_md=eval_md,
            ab_md=ab_md,
            evolution_md=evolution_md,
        )
        print(
            f"Critérios não atingidos: rows={state.dataset_rows} (min {args.min_dataset_rows}), "
            f"classes={state.n_classes} (min {args.min_classes}). "
            "Use --continue-on-short-dataset para treinar mesmo assim.",
            file=sys.stderr,
        )
        return 2

    rc = _run(
        [
            py,
            str(root / "ml/training/src/split_dataset.py"),
            "--in",
            str(jsonl_path),
            "--out_dir",
            str(split_dir),
            "--seed",
            str(args.split_seed),
        ],
        cwd=root,
    )
    if rc:
        return rc

    meta_path = split_dir / "split_meta.json"
    if meta_path.is_file():
        try:
            state.dataset_version = str(_read_json(meta_path).get("dataset_version") or "")
        except (OSError, json.JSONDecodeError):
            state.dataset_version = ""

    rc = _run(
        [
            py,
            str(root / "ml/training/src/train_seniority.py"),
            "--split_dir",
            str(split_dir),
            "--model_version",
            args.out_model_version,
            "--out_dir",
            str(model_dir),
        ],
        cwd=root,
    )
    if rc:
        return rc

    rc = _run(
        [
            py,
            str(root / "ml/training/src/eval_seniority.py"),
            "--model_dir",
            str(model_dir),
            "--test_jsonl",
            str(split_dir / "test.jsonl"),
            "--out_md",
            str(eval_md),
            "--metrics_json",
            str(metrics_json),
        ],
        cwd=root,
    )
    if rc:
        return rc

    rc = _run(
        [
            py,
            str(root / "ml/training/src/export_seniority_sklearn_model.py"),
            "--model_dir",
            str(model_dir),
            "--split_meta",
            str(meta_path),
            "--test_metrics_json",
            str(metrics_json),
        ],
        cwd=root,
    )
    if rc:
        return rc

    if metrics_json.is_file():
        try:
            state.metrics = _read_json(metrics_json)
        except (OSError, json.JSONDecodeError):
            state.metrics = {}

    rc = _run(
        [
            py,
            str(root / "ml/training/src/ab_compare_low_confidence.py"),
            "--in_jsonl",
            str(low_path),
            "--model_dir",
            str(model_dir),
            "--out_md",
            str(ab_md),
        ],
        cwd=root,
    )
    if rc:
        return rc

    state.ab_phantom_after_pass1 = _parse_phantom_after(ab_md)
    state.ab_senior_before, state.ab_senior_after = _parse_ab_senior_shares(ab_md)

    if state.ab_phantom_after_pass1 is not None and state.ab_phantom_after_pass1 > 0:
        bumped = _bump_thresholds(dict(DEFAULT_THRESHOLDS))
        _write_threshold_json(thresh_json, bumped)
        state.threshold_bump_applied = True
        state.threshold_recommendations.append(
            f"Aplicado bump offline em `{thresh_json.as_posix()}`: "
            f"senior_prob_threshold={bumped['senior_prob_threshold']}, "
            f"senior_min_bullets={bumped['senior_min_bullets']} (re-executar A/B)."
        )
        if ab_md.is_file():
            pass1 = root / "ml/training/reports/ab_low_confidence_report_pass1.md"
            pass1.write_text(ab_md.read_text(encoding="utf-8"), encoding="utf-8")
        rc = _run(
            [
                py,
                str(root / "ml/training/src/ab_compare_low_confidence.py"),
                "--in_jsonl",
                str(low_path),
                "--model_dir",
                str(model_dir),
                "--out_md",
                str(ab_md),
                "--thresholds_json",
                str(thresh_json),
            ],
            cwd=root,
        )
        if rc:
            return rc
        state.ab_phantom_after_pass2 = _parse_phantom_after(ab_md)
        state.ab_senior_before, state.ab_senior_after = _parse_ab_senior_shares(ab_md)
        state.threshold_recommendations.append(
            "Para produção: alinhe `SENIOR_PROB_THRESHOLD` / gates em `config/settings` ou env "
            "com os valores em `threshold_gold_scaled_bump.json` (ou rode `tune_thresholds.py`)."
        )
    else:
        state.threshold_recommendations.append(
            "Nenhum bump automático: phantom após ML zero ou relatório não parseável."
        )

    rc = _run(
        [
            py,
            str(root / "ml/training/src/report_dataset_evolution.py"),
            "--jsonl",
            str(jsonl_path),
            "--split_meta",
            str(meta_path),
            "--metrics_json",
            str(metrics_json),
            "--eval_md",
            str(eval_md),
            "--ab_md",
            str(ab_md),
            "--out",
            str(evolution_md),
        ],
        cwd=root,
    )
    if rc:
        return rc

    if state.done_count < args.target_done:
        state.threshold_recommendations.append(
            f"DONE count ({state.done_count}) < target-done ({args.target_done}); "
            "aumente --max-iterations ou --seed-increment se precisar de mais volume para este utilizador."
        )

    _write_gold_summary(
        summary_md,
        args=args,
        state=state,
        eval_md=eval_md,
        ab_md=ab_md,
        evolution_md=evolution_md,
    )

    # Treino concluído; critérios de volume já validados ou ignorados com --continue-on-short-dataset.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
