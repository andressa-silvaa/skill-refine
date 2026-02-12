"""
Report dataset statistics: counts by label, language, task_type, split.
Optionally write ml/reports/dataset_stats.md (total by language, distribution by class, examples, heuristic vs revisado).
Reads JSONL (single file or directory of train/val/test).
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ML_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = ML_ROOT / "reports"
MAX_SAMPLE_LEN = 120


def stats_single(path: Path) -> dict:
    """Compute stats for one JSONL file (task-type and unified)."""
    by_task: dict[str, int] = defaultdict(int)
    by_language: dict[str, int] = defaultdict(int)
    by_label: dict[str, int] = defaultdict(int)
    by_seniority: dict[str, int] = defaultdict(int)
    by_label_source: dict[str, int] = defaultdict(int)
    by_source: dict[str, int] = defaultdict(int)
    total = 0
    samples_by_seniority: dict[str, list[str]] = defaultdict(list)
    max_samples_per_class = 3
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            total += 1
            task = row.get("task_type") or "unified"
            by_task[task] += 1
            lang = row.get("language", "?")
            if isinstance(lang, str):
                lang_norm = lang.replace("-BR", "").replace("-US", "").replace("-ES", "")
            else:
                lang_norm = str(lang)
            by_language[lang_norm] += 1
            label = row.get("label")
            if label:
                by_label[label] += 1
            labels = row.get("labels") or {}
            if isinstance(labels, dict):
                sr = labels.get("seniority")
                if sr:
                    by_seniority[sr] += 1
                    if len(samples_by_seniority[sr]) < max_samples_per_class:
                        text = (row.get("resume_text") or row.get("input_text") or "")[:MAX_SAMPLE_LEN]
                        if text:
                            samples_by_seniority[sr].append(text + ("..." if len(row.get("resume_text") or row.get("input_text") or "") > MAX_SAMPLE_LEN else ""))
            ls = row.get("label_source") or "?"
            by_label_source[ls] += 1
            src = row.get("source") or "?"
            by_source[src] += 1
    return {
        "total": total,
        "by_task": dict(by_task),
        "by_language": dict(by_language),
        "by_label": dict(by_label),
        "by_seniority": dict(by_seniority),
        "by_label_source": dict(by_label_source),
        "by_source": dict(by_source),
        "samples_by_seniority": dict(samples_by_seniority),
    }


def run(input_path: Path) -> dict:
    """Input_path: JSONL file or directory containing train.jsonl, val.jsonl, test.jsonl."""
    if input_path.is_file():
        return {"file": str(input_path), "stats": stats_single(input_path)}
    out: dict = {"splits": {}}
    for name in ("train", "val", "test"):
        p = input_path / f"{name}.jsonl"
        if p.exists():
            out["splits"][name] = stats_single(p)
    return out


def _aggregate_for_md(report: dict) -> tuple[int, dict, dict, dict, dict, dict]:
    """Aggregate totals and by_language, by_seniority, by_label_source, by_source, samples."""
    total = 0
    by_lang: dict[str, int] = defaultdict(int)
    by_seniority: dict[str, int] = defaultdict(int)
    by_label_source: dict[str, int] = defaultdict(int)
    by_source: dict[str, int] = defaultdict(int)
    samples: dict[str, list[str]] = defaultdict(list)
    if "stats" in report:
        s = report["stats"]
        total = s.get("total", 0)
        for k, v in (s.get("by_language") or {}).items():
            by_lang[k] += v
        for k, v in (s.get("by_seniority") or {}).items():
            by_seniority[k] += v
        for k, v in (s.get("by_label_source") or {}).items():
            by_label_source[k] += v
        for k, v in (s.get("by_source") or {}).items():
            by_source[k] += v
        for k, v in (s.get("samples_by_seniority") or {}).items():
            samples[k].extend(v[:3])
    if "splits" in report:
        for name, s in report["splits"].items():
            total += s.get("total", 0)
            for k, v in (s.get("by_language") or {}).items():
                by_lang[k] += v
            for k, v in (s.get("by_seniority") or {}).items():
                by_seniority[k] += v
            for k, v in (s.get("by_label_source") or {}).items():
                by_label_source[k] += v
            for k, v in (s.get("by_source") or {}).items():
                by_source[k] += v
            for k, v in (s.get("samples_by_seniority") or {}).items():
                samples[k].extend(v[:2])
    return total, dict(by_lang), dict(by_seniority), dict(by_label_source), dict(by_source), dict(samples)


def write_dataset_stats_md(report: dict, output_path: Path) -> None:
    """Generate dataset_stats.md: total by language, distribution by class, examples, heuristic vs revisado."""
    total, by_lang, by_seniority, by_label_source, by_source, samples = _aggregate_for_md(report)
    lines = [
        "# Dataset Statistics",
        "",
        "Generated by `scripts/stats_report.py --report-md`.",
        "",
        "## Total",
        "",
        f"- **Total de exemplos:** {total}",
        "",
        "## Por idioma",
        "",
        "| Idioma | Quantidade |",
        "|--------|------------|",
    ]
    for lang in sorted(by_lang.keys()):
        lines.append(f"| {lang} | {by_lang[lang]} |")
    lines.extend([
        "",
        "## Distribuição por classe (senioridade)",
        "",
        "| Classe | Quantidade |",
        "|--------|------------|",
    ])
    for cls in sorted(by_seniority.keys()):
        lines.append(f"| {cls} | {by_seniority[cls]} |")
    lines.extend([
        "",
        "## Fonte dos rótulos (heurística vs revisado)",
        "",
        "| Fonte | Quantidade |",
        "|-------|------------|",
    ])
    for src in sorted(by_label_source.keys()):
        lines.append(f"| {src} | {by_label_source[src]} |")
    lines.extend([
        "",
        "## Fonte dos dados",
        "",
        "| Fonte | Quantidade |",
        "|-------|------------|",
    ])
    for src in sorted(by_source.keys()):
        lines.append(f"| {src} | {by_source[src]} |")
    if samples:
        lines.extend([
            "",
            "## Exemplos anonimizados por classe (preview)",
            "",
        ])
        for cls in sorted(samples.keys()):
            lines.append(f"### {cls}")
            for i, ex in enumerate(samples[cls][:3], 1):
                lines.append(f"- Exemplo {i}: `{ex[:100]}...`" if len(ex) > 100 else f"- Exemplo {i}: `{ex}`")
            lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Dataset statistics report")
    p.add_argument("input", type=Path, help="JSONL file or splits directory")
    p.add_argument("-o", "--output", type=Path, help="Write JSON report here")
    p.add_argument("--report-md", type=Path, nargs="?", const=REPORTS_DIR / "dataset_stats.md", default=None, help="Write dataset_stats.md (default: ml/reports/dataset_stats.md)")
    args = p.parse_args()
    report = run(args.input)
    s = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(s, encoding="utf-8")
    else:
        print(s)
    if args.report_md is not None:
        write_dataset_stats_md(report, args.report_md)
        print(f"Report written: {args.report_md}", flush=True)


if __name__ == "__main__":
    main()
