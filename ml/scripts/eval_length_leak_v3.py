"""
A sonda de senioridade lê comprimento como pista de banda? Ablação controlada.

Motivo: vinte currículos escritos à mão, com 72 palavras de mediana, saíram **zero senior** — incluindo
um de 15,6 anos que lidera nove pessoas e outro de 12,5 anos que coordena vinte e dois. No corpus a
mesma cabeça acerta 98% dos senior. Não é cabeça quebrada, é transferência.

O suspeito, medido antes desta ablação:

    corpus intern   166 palavras/currículo   14,3 palavras/bullet
    corpus junior   164                      15,0
    corpus mid      233                      16,9
    corpus senior   222                      18,7
    escritos à mão   72                      11,8

Comprimento correlaciona com banda no corpus, e os currículos à mão ficam abaixo do piso de tudo que a
sonda viu. É a armadilha da §5.3 um nível abaixo: o número de bullets foi descorrelacionado da banda,
o comprimento de cada bullet não.

O teste: truncar todo currículo para o mesmo número de palavras e remedir a acurácia por banda. Se a
acurácia de senior desabar quando todos têm o comprimento de um intern, o comprimento era a pista — e
parte dos 75,9% de held-out mede artefato do gerador, não o construto.

Usage:
  ./backend/.venv/Scripts/python.exe ml/scripts/eval_length_leak_v3.py
"""
from __future__ import annotations

import argparse
import collections
import os
import statistics
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for extra in (str(REPO_ROOT / "backend" / "src"), str(Path(__file__).resolve().parent)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["ANALYSIS_EMBEDDINGS_ENABLED"] = "true"
os.environ["ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED"] = "true"

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

import label_seniority_llm_v3 as base  # noqa: E402

from apps.analysis.application.inference.config import get_config  # noqa: E402
from apps.analysis.application.inference.tasks.seniority.text.loader_seniority_probe import (  # noqa: E402
    get_seniority_probe_bundle,
)
from apps.analysis.application.inference.tasks.seniority.text.predict import (  # noqa: E402
    predict_text_seniority,
)
from apps.analysis.application.inference.tasks.target_fit.loader_embeddings import (  # noqa: E402
    get_embeddings_model,
)
from apps.analysis.application.inference.text_sanitizer import resume_to_text_sanitized  # noqa: E402

REPORT_PATH = REPO_ROOT / "ml" / "reports" / "length_leak_v3.md"
BANDS = ("intern", "junior", "mid", "senior")
BUDGETS = (None, 220, 160, 110, 72)


def clip_resume(resume_data: dict, budget: int | None) -> dict:
    """
    Encurta o currículo mantendo a ESTRUTURA: resumo, cargos, bullets e formação continuam existindo,
    cada bloco só fica menor. Empilhar tudo num campo destrói o layout de quatro seções que a sonda
    espera, e mede a destruição em vez do comprimento — foi o erro da primeira versão deste script.
    """
    import copy

    if budget is None:
        return resume_data
    out = copy.deepcopy(resume_data)
    data = out.get("data") if isinstance(out.get("data"), dict) else out
    experiences = data.get("experiences") or []
    n_bullets = sum(len(e.get("description") or []) for e in experiences) or 1
    # o resumo leva um quinto do orcamento, o resto se divide entre os bullets
    summary_budget = max(8, budget // 5)
    per_bullet = max(4, (budget - summary_budget) // n_bullets)
    data["summary"] = " ".join(str(data.get("summary") or "").split()[:summary_budget])
    for exp in experiences:
        exp["description"] = [
            " ".join(str(b).split()[:per_bullet]) for b in (exp.get("description") or [])
        ]
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-band", type=int, default=120)
    args = parser.parse_args()

    config = get_config(settings)
    probe = get_seniority_probe_bundle(config)
    encoder = get_embeddings_model(settings)
    if probe is None or encoder is None:
        raise SystemExit("probe ou encoder indisponivel")

    by_band: dict[str, list[dict]] = {}
    for row in base.load_rows():
        band = str(row.get("band_target") or "")
        if band in BANDS and isinstance(row.get("resume_data"), dict):
            by_band.setdefault(band, []).append(row)
    sample = {b: by_band.get(b, [])[: args.per_band] for b in BANDS}

    texts: dict[str, list[tuple[dict, str]]] = {}
    for band, rows in sample.items():
        texts[band] = [(r["resume_data"], str(r.get("language") or "pt-BR")) for r in rows]

    out: list[str] = []
    out.append("# A sonda de senioridade lê comprimento como pista de banda?")
    out.append("")
    out.append(
        f"Gerado {date.today().isoformat()} · até {args.per_band} currículos por banda · "
        "`text_seniority_probe_v1`, texto truncado por orçamento de palavras."
    )
    out.append("")
    out.append("## Comprimento por banda no corpus")
    out.append("")
    out.append("| banda | n | palavras/currículo (mediana) |")
    out.append("|---|---|---|")
    for band in BANDS:
        lens = [len(resume_to_text_sanitized(rd).split()) for rd, _l in texts[band]]
        if lens:
            out.append(f"| {band} | {len(lens)} | {statistics.median(lens):.0f} |")
    out.append("")
    out.append(
        "Se essas medianas subissem com a banda, um modelo só-texto pode acertar contando palavras "
        "em vez de julgando escopo."
    )
    out.append("")
    out.append("## Acurácia por banda, truncando todos para o mesmo orçamento")
    out.append("")
    header = "| orçamento | " + " | ".join(BANDS) + " | média |"
    out.append(header)
    out.append("|---|" + "---|" * (len(BANDS) + 1))

    for budget in BUDGETS:
        per_band_acc = []
        cells = []
        for band in BANDS:
            hits = 0
            total = 0
            for resume_data, lang in texts[band]:
                clipped_data = clip_resume(resume_data, budget)
                pred = predict_text_seniority(
                    resume_to_text_sanitized(clipped_data), lang, None,
                    allow_lexical_fallback=False, probe_bundle=probe,
                    embeddings_model=encoder, resume_data=clipped_data,
                )
                total += 1
                hits += int(str(pred.get("label")) == band)
            acc = hits / max(1, total)
            per_band_acc.append(acc)
            cells.append(f"{acc:.0%}")
        label = "sem corte" if budget is None else f"{budget} palavras"
        mean = statistics.mean(per_band_acc)
        out.append(f"| {label} | " + " | ".join(cells) + f" | **{mean:.0%}** |")
    out.append("")
    out.append(
        "A linha `72 palavras` é o comprimento mediano dos currículos escritos à mão que produziram "
        "zero senior em produção. Se a coluna `senior` desabar ali, o comprimento era a pista."
    )
    out.append("")
    out.append("## Como ler")
    out.append("")
    out.append(
        "- Truncar remove conteúdo junto com comprimento, então parte de qualquer queda é perda de "
        "informação legítima. O que denuncia vazamento é a queda ser **desigual entre bandas**: "
        "senior e mid perderem muito mais que intern e junior significa que o sinal deles morava no "
        "excedente de texto, não no que o texto diz."
    )
    out.append(
        "- Isto não mede currículo real. Mede se a cabeça sobrevive ao comprimento que currículo real "
        "tem."
    )
    text_out = "\n".join(out)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text_out + "\n", encoding="utf-8")
    print(text_out.encode("ascii", "replace").decode("ascii"))
    print(f"\nwrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
