"""
Score the human review of the LLM labels — the only place where a person, not a model, decides.

Everything else in the pipeline is model against model (two teachers) or model against generator
(label against the planted target). Both can be jointly wrong. This reads the filled verdicts and
answers the question a defence will ask: when the teacher and the generator disagree, which one does
a human side with?

Three numbers come out of it:

  1. teacher accuracy on the sample, and separately on stratum C, which is the only stratum drawn
     without bias — A oversamples disagreements on purpose, so scoring A and C together understates
     the teacher.
  2. who the human backs on the disagreements. Human siding with the teacher means the generator's
     planted band is the wrong one on those rows, which is the interesting outcome: the teacher read
     something the formula could not.
  3. `impact` agreement, the human anchor for the pillar worth 78% of the score.

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/score_label_review.py
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "resumes_v3"
BANDS = ("intern", "junior", "mid", "senior")
ORDER = {b: i for i, b in enumerate(BANDS)}


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"missing {path} — run build_label_review_sample.py first")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _human_band(row: dict[str, Any]) -> str | None:
    raw = str(row.get("verdict") or "").strip().lower()
    if not raw:
        return None
    if raw == "ok":
        return str(row["llm_label"])
    if raw in ORDER:
        return raw
    return None


def _pct(hit: int, total: int) -> str:
    return f"{hit}/{total} ({hit / total:.0%})" if total else "sem dados"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verdicts", default="review_verdicts.jsonl")
    args = parser.parse_args()

    rows = _read(DATA_DIR / args.verdicts)
    filled = [r for r in rows if _human_band(r)]
    print(f"amostra: {len(rows)} linhas | revisadas: {len(filled)}")
    if not filled:
        print("nenhum verdict preenchido ainda")
        return 0
    invalid = [
        r["id"]
        for r in rows
        if str(r.get("verdict") or "").strip() and _human_band(r) is None
    ]
    if invalid:
        print(f"AVISO: verdict invalido em {len(invalid)} linha(s): {', '.join(invalid[:5])}")
        print("  use intern | junior | mid | senior | ok")

    print("\n" + "=" * 70)
    print("O PROFESSOR CONTRA O HUMANO")
    print("=" * 70)
    hit = sum(1 for r in filled if _human_band(r) == r["llm_label"])
    near = sum(1 for r in filled if abs(ORDER[_human_band(r)] - ORDER[r["llm_label"]]) <= 1)
    print(f"  concordancia de banda: {_pct(hit, len(filled))}   ±1 nivel: {_pct(near, len(filled))}")

    by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in filled:
        by_stratum[str(row.get("reason") or "?")[:1]].append(row)
    labels = {
        "A": "discordancias professor x gerador (super-amostrado)",
        "B": "grupos com divergencia de idioma",
        "C": "linha de base, a unica estimativa nao viesada",
    }
    for key in sorted(by_stratum):
        subset = by_stratum[key]
        ok = sum(1 for r in subset if _human_band(r) == r["llm_label"])
        print(f"  estrato {key} — {labels.get(key, '')}: {_pct(ok, len(subset))}")

    print("\n" + "=" * 70)
    print("NAS DISCORDANCIAS, DE QUEM O HUMANO FICA DO LADO")
    print("=" * 70)
    contested = [r for r in filled if r["llm_label"] != r["band_target"]]
    if not contested:
        print("  nenhuma linha contestada na amostra revisada")
    else:
        with_teacher = sum(1 for r in contested if _human_band(r) == r["llm_label"])
        with_target = sum(1 for r in contested if _human_band(r) == r["band_target"])
        neither = len(contested) - with_teacher - with_target
        print(f"  linhas contestadas: {len(contested)}")
        print(f"    com o professor: {_pct(with_teacher, len(contested))}")
        print(f"    com o alvo plantado: {_pct(with_target, len(contested))}")
        print(f"    com nenhum dos dois: {_pct(neither, len(contested))}")
        if with_teacher > with_target:
            print("  leitura: o professor le no texto o que a formula do gerador nao ve")
        elif with_target > with_teacher:
            print("  leitura: o professor erra onde o gerador acerta — revisar a rubrica")

    print("\n" + "=" * 70)
    print("POR IDIOMA E POR BANDA")
    print("=" * 70)
    for field, title in (("language", "idioma"), ("llm_label", "banda do professor")):
        buckets: dict[str, list[int]] = defaultdict(list)
        for row in filled:
            buckets[str(row.get(field))].append(int(_human_band(row) == row["llm_label"]))
        line = "  ".join(f"{k}: {_pct(sum(v), len(v))}" for k, v in sorted(buckets.items()))
        print(f"  {title}: {line}")

    print("\n" + "=" * 70)
    print("IMPACT: ANCORA HUMANA DO PILAR DE 78%")
    print("=" * 70)
    pairs = []
    for row in rows:
        raw = str(row.get("impact_verdict") or "").strip()
        if not raw:
            continue
        try:
            human = int(round(float(raw)))
        except ValueError:
            continue
        llm = row.get("llm_impact")
        if isinstance(llm, (int, float)):
            pairs.append((max(1, min(5, human)), int(llm)))
    if not pairs:
        print("  nenhum impact_verdict preenchido — o professor de qualidade fica sem ancora humana")
    else:
        mae = sum(abs(a - b) for a, b in pairs) / len(pairs)
        exact = sum(1 for a, b in pairs if a == b)
        within = sum(1 for a, b in pairs if abs(a - b) <= 1)
        bias = sum(a - b for a, b in pairs) / len(pairs)
        print(f"  n={len(pairs)}  erro medio {mae:.2f} ponto  exato {_pct(exact, len(pairs))}"
              f"  ±1 {_pct(within, len(pairs))}")
        print(f"  vies (humano - professor): {bias:+.2f} — negativo = professor generoso")
        by_target: dict[str, list[int]] = defaultdict(list)
        for row, (human, _llm) in zip([r for r in rows if str(r.get("impact_verdict") or "").strip()], pairs):
            if row.get("quality_target"):
                by_target[str(row["quality_target"])].append(human)
        if by_target:
            print("  nota humana media por qualidade plantada:")
            for target in ("poor", "fair", "good"):
                values = by_target.get(target) or []
                if values:
                    print(f"    {target:<5} n={len(values):3d}  {sum(values) / len(values):.2f}")

    print("\ncomposicao revisada:", dict(Counter(str(r.get("reason"))[:1] for r in filled)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
