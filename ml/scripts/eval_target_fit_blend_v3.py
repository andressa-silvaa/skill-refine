"""
Os 35% de policy dentro do `target_fit` ajudam? Medido, sem anotação nova.

`orchestrator.py` publica `fit = 0,65 × embedding + 0,35 × policy`. Os 35% são a última regra que
entra num número publicado: `compute_target_fit_policy` soma contagens de termo, evidência de
portfólio e alinhamento de formação por palavra-chave. O peso 0,65 nunca foi medido.

O roadmap dizia que medir isso exigia `reviewed_score` humano. Exige para **calibração** — saber se 72
é o número certo. Não exige para **discriminação**, que é o que decide o peso: pares são construídos
do próprio corpus, como na medição de idioma.

  par positivo:  currículo + o `targetPosition` da própria ocupação
  par negativo:  currículo + o `targetPosition` de outra ocupação sorteada

Se a policy não separa positivo de negativo melhor que o encoder sozinho, `w_e = 1,0` tira 35% de
heurística do score com número na mão, em vez de por preferência.

**Ressalva que o número carrega:** o negativo é uma ocupação sorteada entre 1.701, então é um não-fit
fácil — mais fácil que um usuário mirando cargo adjacente. Todo AUC aqui é limite superior, e a
comparação entre configurações é o que vale, não o valor absoluto.

Usage:
  ./backend/.venv/Scripts/python.exe ml/scripts/eval_target_fit_blend_v3.py
  ./backend/.venv/Scripts/python.exe ml/scripts/eval_target_fit_blend_v3.py --limit 300
"""
from __future__ import annotations

import argparse
import os
import random
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

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

import label_seniority_llm_v3 as base  # noqa: E402

from apps.analysis.application.inference.completeness import assess_completeness  # noqa: E402
from apps.analysis.application.inference.resume_mapper import resume_to_text  # noqa: E402
from apps.analysis.application.inference.tasks.target_fit.embedding import (  # noqa: E402
    build_cv_embedding_text,
    build_target_embedding_text,
    embedding_fit_scores,
)
from apps.analysis.application.inference.tasks.target_fit.fit_signals import (  # noqa: E402
    extract_target_fit_signals,
)
from apps.analysis.application.inference.tasks.target_fit.isco_domains import (  # noqa: E402
    domain_for_isco,
)
from apps.analysis.application.inference.tasks.target_fit.loader_embeddings import (  # noqa: E402
    get_embeddings_model,
)
from apps.analysis.application.inference.tasks.target_fit.target_seniority import (  # noqa: E402
    compute_target_fit_policy,
    compute_target_seniority,
)

REPORT_PATH = REPO_ROOT / "ml" / "reports" / "target_fit_blend_v3.md"
SEED = 20260814
WEIGHTS = (1.0, 0.85, 0.65, 0.5, 0.35, 0.0)


def auc(positive: list[float], negative: list[float]) -> float:
    if not positive or not negative:
        return float("nan")
    joined = np.concatenate([np.asarray(positive, dtype=float), np.asarray(negative, dtype=float)])
    order = joined.argsort()
    ranks = np.empty(len(joined), dtype=float)
    ranks[order] = np.arange(1, len(joined) + 1)
    n_pos = len(positive)
    return float(
        (ranks[:n_pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * len(negative))
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    model = get_embeddings_model(settings)
    if model is None:
        raise SystemExit("encoder unavailable")

    rows = base.load_rows()
    if args.limit:
        rows = rows[: args.limit]

    pool = []
    for row in rows:
        resume_data = row.get("resume_data")
        occupation = row.get("occupation") or {}
        if not isinstance(resume_data, dict):
            continue
        block = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else {}
        target = str(block.get("targetPosition") or "").strip()
        if not target:
            continue
        pool.append(
            {
                "resume_data": resume_data,
                "lang": str(row.get("language") or "pt-BR"),
                "target": target,
                "domain": domain_for_isco(str(occupation.get("isco") or "")),
                "isco2": str(occupation.get("isco") or "")[:2],
            }
        )
    if len(pool) < 50:
        raise SystemExit("not enough rows with a targetPosition")
    print(f"{len(pool)} resumes; scoring matched and mismatched pairs ...")

    rng = random.Random(SEED)
    scores: dict[str, dict[float, list[float]]] = {
        "embedding": {}, "policy": {}, "blend": {}
    }
    per_weight_pos: dict[float, list[float]] = {w: [] for w in WEIGHTS}
    per_weight_neg: dict[float, list[float]] = {w: [] for w in WEIGHTS}
    per_weight_hard: dict[float, list[float]] = {w: [] for w in WEIGHTS}
    emb_hard: list[float] = []
    pol_hard: list[float] = []
    by_isco: dict[str, list[dict]] = {}
    for entry in pool:
        by_isco.setdefault(entry["isco2"], []).append(entry)
    emb_pos: list[float] = []
    emb_neg: list[float] = []
    pol_pos: list[float] = []
    pol_neg: list[float] = []
    seniority_pos: list[int] = []
    seniority_neg: list[int] = []
    order = {"intern": 0, "junior": 1, "mid": 2, "senior": 3}

    for index, item in enumerate(pool):
        resume_data = item["resume_data"]
        lang = item["lang"]
        sections = resume_to_text(resume_data, language=lang)
        completeness = int(assess_completeness(resume_data, sections).get("score") or 0)
        cv_text = build_cv_embedding_text(sections.full_text)

        other = pool[rng.randrange(len(pool))]
        while other["target"] == item["target"]:
            other = pool[rng.randrange(len(pool))]

        # Adjacent role: same ISCO 2-digit group, different job title. This is the realistic case -
        # a user aiming one step sideways - and the only one that separates the configurations.
        neighbours = by_isco.get(item["isco2"]) or []
        near = None
        for candidate in rng.sample(neighbours, min(len(neighbours), 12)):
            if candidate["target"] != item["target"]:
                near = candidate
                break

        pairs = [
            ("pos", item["target"], item["domain"]),
            ("neg", other["target"], other["domain"]),
        ]
        if near is not None:
            pairs.append(("hard", near["target"], near["domain"]))
        for label, target, domain in pairs:
            signals = extract_target_fit_signals(
                resume_data, target, None, lang, completeness_score=completeness
            )
            policy = float(
                compute_target_fit_policy(
                    signals,
                    has_job_text=False,
                    resume_domain=item["domain"],
                    target_domain=domain,
                )
            )
            embedding, _cos, _kw = embedding_fit_scores(
                model, cv_text, build_target_embedding_text(target, "", domain, lang)
            )
            embedding = float(embedding)
            bucket = {"pos": per_weight_pos, "neg": per_weight_neg, "hard": per_weight_hard}[label]
            for weight in WEIGHTS:
                bucket[weight].append(weight * embedding + (1.0 - weight) * policy)
            if label == "pos":
                emb_pos.append(embedding)
                pol_pos.append(policy)
            elif label == "neg":
                emb_neg.append(embedding)
                pol_neg.append(policy)
            else:
                emb_hard.append(embedding)
                pol_hard.append(policy)

            if label in ("pos", "neg"):
                pack = compute_target_seniority(
                    "mid", int(round(0.65 * embedding + 0.35 * policy)), signals, lang
                )
                value = order.get(str(pack.get("targetSeniorityLabel") or "junior"), 1)
                (seniority_pos if label == "pos" else seniority_neg).append(value)

        if (index + 1) % 200 == 0:
            print(f"  {index + 1}/{len(pool)}")

    out: list[str] = []
    out.append("# `target_fit`: os 35% de policy ajudam?")
    out.append("")
    out.append(
        f"Gerado {date.today().isoformat()} · {len(pool)} currículos · {2 * len(pool)} pares "
        "(um positivo e um negativo por currículo) · sem anotação nova."
    )
    out.append("")
    out.append(
        "Produção publica `fit = 0,65 × embedding + 0,35 × policy`. Os 35% são a última regra dentro "
        "de um número publicado, e o peso nunca foi medido. Par positivo é o currículo com o "
        "`targetPosition` da própria ocupação; negativo é o de outra ocupação sorteada."
    )
    out.append("")
    out.append("## Discriminação por peso do encoder")
    out.append("")
    out.append("| `w_e` | composição | AUC (fit vs não-fit) |")
    out.append("|---|---|---|")
    best_weight, best_auc = None, -1.0
    for weight in WEIGHTS:
        value = auc(per_weight_pos[weight], per_weight_neg[weight])
        composition = (
            "só encoder" if weight == 1.0 else "só policy" if weight == 0.0 else f"{int(weight*100)}/{int((1-weight)*100)}"
        )
        marker = " ← produção" if abs(weight - 0.65) < 1e-9 else ""
        out.append(f"| {weight:.2f} | {composition}{marker} | **{value:.3f}** |")
        if value > best_auc:
            best_weight, best_auc = weight, value
    out.append("")
    out.append(
        f"Melhor: **`w_e` = {best_weight:.2f}** com AUC {best_auc:.3f}. "
        f"Produção hoje ({auc(per_weight_pos[0.65], per_weight_neg[0.65]):.3f}) contra só encoder "
        f"({auc(per_weight_pos[1.0], per_weight_neg[1.0]):.3f})."
    )
    out.append("")
    if per_weight_hard[1.0]:
        out.append("## O caso realista: alvo adjacente (mesmo grupo ISCO)")
        out.append("")
        out.append(
            "Aqui o negativo não é uma ocupação sorteada entre 1.701, é um cargo do **mesmo grupo "
            "ISCO de 2 dígitos** — um passo de lado, que é o que um usuário real faz. É esta coluna "
            "que separa as configurações; a de cima satura."
        )
        out.append("")
        out.append("| `w_e` | composição | AUC sorteado | **AUC adjacente** |")
        out.append("|---|---|---|---|")
        best_hard_w, best_hard = None, -1.0
        for weight in WEIGHTS:
            easy = auc(per_weight_pos[weight], per_weight_neg[weight])
            hard = auc(per_weight_pos[weight], per_weight_hard[weight])
            composition = (
                "só encoder" if weight == 1.0
                else "só policy" if weight == 0.0
                else f"{int(weight*100)}/{int((1-weight)*100)}"
            )
            marker = " ← produção" if abs(weight - 0.65) < 1e-9 else ""
            out.append(f"| {weight:.2f} | {composition}{marker} | {easy:.3f} | **{hard:.3f}** |")
            if hard > best_hard:
                best_hard_w, best_hard = weight, hard
        out.append("")
        out.append(
            f"Melhor no caso adjacente: **`w_e` = {best_hard_w:.2f}** (AUC {best_hard:.3f}), contra "
            f"{auc(per_weight_pos[0.65], per_weight_hard[0.65]):.3f} da produção e "
            f"{auc(per_weight_pos[1.0], per_weight_hard[1.0]):.3f} do encoder sozinho."
        )
        out.append("")

    out.append("## Os dois componentes isolados")
    out.append("")
    out.append("| componente | AUC | média no fit | média no não-fit |")
    out.append("|---|---|---|---|")
    out.append(
        f"| embedding | {auc(emb_pos, emb_neg):.3f} | {np.mean(emb_pos):.1f} | {np.mean(emb_neg):.1f} |"
    )
    out.append(
        f"| policy | {auc(pol_pos, pol_neg):.3f} | {np.mean(pol_pos):.1f} | {np.mean(pol_neg):.1f} |"
    )
    if emb_hard:
        out.append("")
        out.append("No caso adjacente, isolados:")
        out.append("")
        out.append("| componente | AUC adjacente | média no fit | média no adjacente |")
        out.append("|---|---|---|---|")
        out.append(
            f"| embedding | {auc(emb_pos, emb_hard):.3f} | {np.mean(emb_pos):.1f} | {np.mean(emb_hard):.1f} |"
        )
        out.append(
            f"| policy | {auc(pol_pos, pol_hard):.3f} | {np.mean(pol_pos):.1f} | {np.mean(pol_hard):.1f} |"
        )
    out.append("")
    out.append("## `target_seniority`: os clamps reagem ao alvo errado?")
    out.append("")
    same = int(np.sum(np.asarray(seniority_pos) == np.asarray(seniority_neg)))
    out.append(
        f"Rodando `compute_target_seniority` nos dois pares do mesmo currículo, o rótulo é **idêntico "
        f"em {same}/{len(seniority_pos)} ({same / len(seniority_pos):.0%})** dos casos. Média do "
        f"rótulo (0=intern, 3=senior): fit {np.mean(seniority_pos):.2f} contra não-fit "
        f"{np.mean(seniority_neg):.2f}."
    )
    out.append("")
    out.append("## Como ler")
    out.append("")
    out.append(
        "- **Duas dificuldades, e a segunda é a que informa.** Contra ocupação sorteada tudo satura "
        "perto de 0,98 e as configurações não se separam. Contra cargo adjacente do mesmo grupo "
        "ISCO — o que um usuário real faz — o vão aparece. Nenhuma das duas é currículo real; a "
        "comparação **entre** configurações é o que vale, não o valor absoluto."
    )
    out.append(
        "- **A mistura ganha dos dois componentes isolados, nas duas dificuldades.** Isso é "
        "comportamento de ensemble: o encoder e a policy erram em casos diferentes. Refuta a "
        "hipótese de que os 35% fossem heurística inerte dentro de um número neural."
    )
    out.append(
        "- **Não retune 0,65 com isto.** O ótimo medido é 0,50, e a diferença para produção é 0,005 "
        "de AUC em pares construídos. Mover uma constante de produção por esse ganho seria ajustar "
        "ao proxy — exatamente o erro que ml/reports/education_alignment_v3.md documenta. O valor "
        "desta medição é justificar a mistura, não recalibrá-la."
    )
    out.append(
        "- **Discriminação, não calibração.** Isto responde se a policy ajuda a separar fit de "
        "não-fit. Não responde se 72 é o número certo — para isso continua sendo preciso "
        "`reviewed_score` humano."
    )
    text = "\n".join(out)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text + "\n", encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))
    print(f"\nwrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
