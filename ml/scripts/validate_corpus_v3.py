"""
Validate the v3 synthetic corpus against the failure modes that broke the v2 model.

Runs the REAL product feature extractor (extract_resume_signals) over the generated resumes,
then checks the properties the corpus must have. Safe to run mid-generation on a partial file.

Checks, each tied to a concrete past failure:
  1. realism  — do the 4 real resumes fall INSIDE the generated feature ranges? v2 failed
     because training summary_char_count spanned 30-61 chars while real resumes span 183-360,
     putting real input ~25 sigma out and collapsing the classifier to a single class.
  2. leakage  — summary_char_count / bullets_count must NOT separate the bands, or the model
     will read the answer off a structural count instead of tenure and scope.
  3. contamination — ISCO major group must carry no band signal, else "domain" is a shortcut.
  4. language — bands must be balanced within every language, and parallel groups intact.
  5. diversity — bullets must not be recycled across resumes, or the text model memorises
     phrases instead of learning language.

REAL_REFERENCE holds signals measured from the 4 resumes in the production database on
2026-08-06 (dev front end, Analista Financeiro, Desenvolvedor Full Stack, Engenheiro Civil).

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/validate_corpus_v3.py
"""
from __future__ import annotations

import json
import os
import statistics
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
from apps.analysis.application.inference.signals.resume_signals import (  # noqa: E402
    extract_resume_signals,
)

PROSE_PATH = REPO_ROOT / "ml" / "data" / "raw" / "resumes_v3" / "prose.jsonl"
BANDS = ("intern", "junior", "mid", "senior")

MIN_N_FOR_VERDICT = 200
MIN_N_PER_ISCO_GROUP = 30

COUNT_AUC_TOLERANCE = 0.30
MONTHS_AUC_FLOOR = 0.90

REAL_REFERENCE = {
    "dev front end": {"months": 3, "bullets": 1, "experiences": 1, "summary_chars": 183},
    "Analista Financeiro": {
        "months": 99, "bullets": 5, "experiences": 2, "summary_chars": 298, "word_count": 119,
    },
    "Desenvolvedor Full Stack": {
        "months": 55, "bullets": 7, "experiences": 2, "summary_chars": 316, "word_count": 153,
    },
    "Engenheiro Civil": {"months": 147, "bullets": 7, "experiences": 2, "summary_chars": 360},
}

FIELD_MAP = {
    "months": "total_months_experience",
    "bullets": "bullets_count",
    "experiences": "experiences_count",
    "summary_chars": "summary_char_count",
    "word_count": "word_count",
}


def load_rows() -> list[dict[str, Any]]:
    if not PROSE_PATH.exists():
        raise SystemExit(f"missing {PROSE_PATH}")
    rows = []
    for line in PROSE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def signals_for(row: dict[str, Any]) -> Any:
    payload = row["resume_data"]
    sections = resume_to_text(payload)
    return extract_resume_signals(payload, sections, row["language"])


def _spread(values: list[float]) -> str:
    if not values:
        return "n/a"
    vs = sorted(values)
    return (
        f"min={vs[0]:.0f} p10={vs[int(len(vs) * 0.10)]:.0f} med={statistics.median(vs):.0f} "
        f"p90={vs[int(len(vs) * 0.90)]:.0f} max={vs[-1]:.0f}"
    )


def _auc(a: list[float], b: list[float]) -> float:
    """
    P(random b > random a), ties counted as half — the Mann-Whitney statistic.

    Rank-based rather than min/max, because a range-overlap measure needs the tails to be
    sampled and reports false alarms at small n. 0.50 means the feature cannot separate the
    two bands at all, which is what we want for every feature except tenure.
    """
    if not a or not b:
        return 0.5
    wins = sum(1.0 if y > x else 0.5 if y == x else 0.0 for x in a for y in b)
    return wins / (len(a) * len(b))


def main() -> None:
    rows = load_rows()
    if not rows:
        raise SystemExit("no rows yet")
    print(f"corpus rows: {len(rows)}\n")

    sig = [(r, signals_for(r)) for r in rows]
    by_band: dict[str, dict[str, list[float]]] = {
        b: defaultdict(list) for b in BANDS
    }
    allv: dict[str, list[float]] = defaultdict(list)
    for r, s in sig:
        for short, attr in FIELD_MAP.items():
            v = float(getattr(s, attr))
            by_band[r["band_target"]][short].append(v)
            allv[short].append(v)

    failures: list[str] = []
    count_aucs: dict[str, float] = {}
    provisional = len(rows) < MIN_N_FOR_VERDICT

    print("=" * 78)
    print("1. REALISMO — os 4 curriculos reais caem dentro da faixa gerada?")
    print("=" * 78)
    for name, ref in REAL_REFERENCE.items():
        parts = []
        for short, real_val in ref.items():
            gen = allv[short]
            inside = min(gen) <= real_val <= max(gen)
            pct = sum(1 for g in gen if g <= real_val) / len(gen) * 100
            parts.append(f"{short}={real_val} {'OK' if inside else 'FORA'} (p{pct:.0f})")
            if not inside:
                failures.append(f"realismo: {name}.{short}={real_val} fora da faixa gerada")
        print(f"  {name[:26]:28s} " + " | ".join(parts))
    print("\n  faixas geradas:")
    for short in FIELD_MAP:
        print(f"    {short:14s} {_spread(allv[short])}")

    print("\n" + "=" * 78)
    print("2. LEAKAGE — contagens estruturais separam as bandas? (queremos SOBREPOSICAO alta)")
    print("=" * 78)
    for short in ("summary_chars", "bullets", "word_count"):
        print(f"  {short}:")
        for b in BANDS:
            vs = by_band[b][short]
            if vs:
                print(f"    {b:7s} n={len(vs):4d} media={statistics.mean(vs):7.1f}  {_spread(vs)}")
        auc = _auc(by_band["intern"][short], by_band["senior"][short])
        dev = abs(auc - 0.5)
        count_aucs[short] = auc
        verdict = "OK" if dev <= COUNT_AUC_TOLERANCE else "RISCO"
        print(f"    AUC senior-vs-intern = {auc:.2f} (0.50 = sem sinal)  [{verdict}]")
        if dev > COUNT_AUC_TOLERANCE:
            failures.append(f"leakage: {short} separa intern de senior (AUC {auc:.2f})")

    print("\n  months (aqui a separacao e ESPERADA — e o sinal legitimo):")
    for b in BANDS:
        vs = by_band[b]["months"]
        if vs:
            print(f"    {b:7s} media={statistics.mean(vs):7.1f}  {_spread(vs)}")
    m_auc = _auc(by_band["intern"]["months"], by_band["senior"]["months"])
    print(f"    AUC senior-vs-intern = {m_auc:.2f} (queremos perto de 1.00)")
    if m_auc < MONTHS_AUC_FLOOR:
        failures.append(f"sinal fraco: months quase nao separa as bandas (AUC {m_auc:.2f})")
    worst_count = max((abs(a - 0.5) for a in count_aucs.values()), default=0.0)
    if worst_count >= abs(m_auc - 0.5):
        failures.append(
            "dominancia: alguma contagem separa as bandas tanto quanto o tempo de experiencia"
        )
    print(
        f"    tenure domina as contagens? {'sim' if worst_count < abs(m_auc - 0.5) else 'NAO'}"
        f" (contagem max={worst_count + 0.5:.2f} vs months={m_auc:.2f})"
    )

    print("\n" + "=" * 78)
    print("3. CONTAMINACAO — grupo ISCO carrega sinal de banda?")
    print("=" * 78)
    major = defaultdict(Counter)
    for r, _ in sig:
        code = str((r.get("occupation") or {}).get("isco") or "?")
        major[code[:1]][r["band_target"]] += 1
    worst = 0.0
    for g in sorted(major):
        c = major[g]
        tot = sum(c.values())
        if tot < MIN_N_PER_ISCO_GROUP:
            print(f"  ISCO {g}x  n={tot:4d}  (amostra pequena, ignorado)")
            continue
        top = max(c.values()) / tot
        worst = max(worst, top)
        flag = "" if top <= 0.45 else "  <-- concentrado"
        print(f"  ISCO {g}x  n={tot:4d}  " + " ".join(f"{b}={c[b]:3d}" for b in BANDS) + flag)
    print(f"\n  maior concentracao de uma banda num grupo = {worst:.2f} (acaso = 0.25)")
    if worst > 0.50:
        failures.append(f"contaminacao: um grupo ISCO concentra {worst:.0%} numa banda")

    print("\n" + "=" * 78)
    print("4. IDIOMA — bandas balanceadas dentro de cada idioma / grupos paralelos")
    print("=" * 78)
    per_lang = defaultdict(Counter)
    for r, _ in sig:
        per_lang[r["language"]][r["band_target"]] += 1
    for lg in sorted(per_lang):
        c = per_lang[lg]
        tot = sum(c.values())
        print(f"  {lg}  n={tot:4d}  " + " ".join(f"{b}={c[b]:3d}" for b in BANDS))
    groups = defaultdict(set)
    for r, _ in sig:
        if r.get("parallel_group"):
            groups[r["parallel_group"]].add(r["language"])
    complete = sum(1 for v in groups.values() if len(v) == 3)
    print(f"  grupos paralelos: {len(groups)} vistos, {complete} completos nos 3 idiomas")

    print("\n" + "=" * 78)
    print("5. DIVERSIDADE — bullets reciclados entre curriculos diferentes?")
    print("=" * 78)
    bullets = [
        b.strip().lower()
        for r, _ in sig
        for e in r["resume_data"]["data"]["experiences"]
        for b in e["description"]
    ]
    uniq = len(set(bullets))
    ratio = uniq / len(bullets) if bullets else 0
    print(f"  bullets totais={len(bullets)} distintos={uniq} ({ratio:.1%} unicos)")
    for text, n in Counter(bullets).most_common(3):
        if n > 1:
            print(f"    x{n}: {text[:88]}")
    if ratio < 0.90:
        failures.append(f"diversidade: apenas {ratio:.1%} dos bullets sao unicos")

    summaries = [
        s for r, _ in sig if (s := r["resume_data"]["data"]["summary"].strip().lower())
    ]
    empty = len(sig) - len(summaries)
    su = len(set(summaries)) / len(summaries) if summaries else 1.0
    print(f"  summaries distintos: {su:.1%} (ignorando {empty} vazios propositais)")
    if su < 0.95:
        failures.append(f"diversidade: apenas {su:.1%} dos summaries sao unicos")

    print("\n" + "=" * 78)
    if provisional:
        print(
            f"PARCIAL — {len(rows)} linhas (< {MIN_N_FOR_VERDICT}). Caudas raras ainda nao"
            " amostradas, entao o veredito abaixo e indicativo, nao final."
        )
    if failures:
        print(f"{'ALERTAS' if provisional else 'REPROVADO'} — {len(failures)} problema(s):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(0 if provisional else 1)
    print("APROVADO — todas as checagens passaram")


if __name__ == "__main__":
    main()
