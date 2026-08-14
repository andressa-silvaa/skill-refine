"""
What does getting the language wrong cost? Measure before installing a detector.

``worker.py`` takes the analysis language from ``UserPreferences.language`` — the user's interface
setting — and never looks at the resume. A Brazilian with a Portuguese UI who uploads an English CV
is analysed as pt-BR, and a user with no saved preference falls back to pt-BR outright. There is no
cheaper source to switch to: ``resume_languages`` is the table of languages the *candidate speaks*,
not the language the document is written in.

The ESCO step is where this bites hardest. It embeds the 1,701 occupation labels **in the resume's
language** and retrieves against that index, so a wrong language compares English resume text with
Portuguese occupation labels. Section 6 reported 85.5% domain accuracy — every one of those numbers
assumed the language was right, because nothing ever tested otherwise.

This script scores every resume twice: once against its own language index (the section 6 baseline)
and once against each wrong-language index, which is exactly what production does when the UI
preference disagrees with the document. The gap is the cost of the missing detector, and it decides
whether one is urgent or merely nice.

Usage:
  ./backend/.venv/Scripts/python.exe ml/scripts/eval_language_mismatch_v3.py
  ./backend/.venv/Scripts/python.exe ml/scripts/eval_language_mismatch_v3.py --limit 300
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
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

from apps.analysis.application.inference.resume_mapper import resume_to_text  # noqa: E402
from apps.analysis.application.inference.tasks.target_fit.esco_retrieval import (  # noqa: E402
    build_occupation_query,
    get_occupation_index,
)
from apps.analysis.application.inference.tasks.target_fit.isco_domains import (  # noqa: E402
    domain_for_isco,
)
from apps.analysis.application.inference.tasks.target_fit.loader_embeddings import (  # noqa: E402
    get_embeddings_model,
)

REPORT_PATH = REPO_ROOT / "ml" / "reports" / "language_mismatch_v3.md"
MODEL_NAME = str(getattr(settings, "ANALYSIS_EMBEDDINGS_MODEL_NAME", "") or "")
LANGS = ("pt", "en", "es")
MAX_QUERY_CHARS = 4000


def lang_key(value: str | None) -> str:
    return str(value or "pt-BR").split("-")[0].lower()


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

    usable = []
    for row in rows:
        occupation = row.get("occupation") or {}
        uri = occupation.get("uri")
        resume_data = row.get("resume_data")
        if not uri or not isinstance(resume_data, dict):
            continue
        usable.append(
            {
                "true_lang": lang_key(row.get("language")),
                "uri": uri,
                "domain": domain_for_isco(str(occupation.get("isco") or "")),
                "query": build_occupation_query(resume_data)[:MAX_QUERY_CHARS]
                or resume_to_text(resume_data, language=row.get("language") or "pt-BR").full_text[
                    :MAX_QUERY_CHARS
                ],
            }
        )
    if not usable:
        raise SystemExit("no rows with an occupation label")
    print(f"scoring {len(usable)} resumes against {len(LANGS)} language indexes ...")

    indexes = {}
    for lang in LANGS:
        index = get_occupation_index(model, lang, max_alt_labels=0, model_name=MODEL_NAME)
        if index is None:
            raise SystemExit(f"occupation index unavailable for {lang}")
        indexes[lang] = index

    embeddings = np.asarray(
        model.encode(
            [r["query"] for r in usable], batch_size=64, show_progress_bar=False, normalize_embeddings=True
        ),
        dtype=np.float32,
    )

    # results[true_lang][assumed_lang] = (occupation top-1 hits, domain hits, n)
    results: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for assumed in LANGS:
        index = indexes[assumed]
        sims = embeddings @ index.matrix.T
        best = sims.argmax(axis=1)
        for position, row in enumerate(usable):
            occupation = index.occupations[index.row_to_occupation[int(best[position])]]
            cell = results[row["true_lang"]][assumed]
            cell[0] += int(str(occupation.get("uri")) == str(row["uri"]))
            cell[1] += int(str(occupation.get("domain") or "general") == str(row["domain"]))
            cell[2] += 1

    out: list[str] = []
    out.append("# Custo de errar o idioma — recuperação de ocupação ESCO")
    out.append("")
    out.append(
        f"Gerado {date.today().isoformat()} · {len(usable)} currículos · encoder "
        f"`{MODEL_NAME or 'MiniLM multilíngue'}` · índice ESCO de 1.701 ocupações por idioma."
    )
    out.append("")
    out.append(
        "`worker.py` toma o idioma de `UserPreferences.language`, a preferência de interface do "
        "usuário, e nunca lê o currículo. A diagonal é o que a §6 mediu; fora dela é o que produção "
        "entrega quando a preferência discorda do documento."
    )
    out.append("")
    out.append("## Acerto de ocupação top-1")
    out.append("")
    out.append("| idioma real \\ assumido | " + " | ".join(LANGS) + " | n |")
    out.append("|---|" + "---|" * (len(LANGS) + 1))
    for true_lang in LANGS:
        if not results[true_lang]:
            continue
        cells = []
        total = 0
        for assumed in LANGS:
            hits, _dom, n = results[true_lang][assumed]
            total = n
            marker = "**" if true_lang == assumed else ""
            cells.append(f"{marker}{hits / n:.1%}{marker}" if n else "—")
        out.append(f"| {true_lang} | " + " | ".join(cells) + f" | {total} |")
    out.append("")

    out.append("## Acerto de domínio — o número que alimenta `careerSwitch` e `target_seniority`")
    out.append("")
    out.append("| idioma real \\ assumido | " + " | ".join(LANGS) + " | n |")
    out.append("|---|" + "---|" * (len(LANGS) + 1))
    for true_lang in LANGS:
        if not results[true_lang]:
            continue
        cells = []
        total = 0
        for assumed in LANGS:
            _occ, domains, n = results[true_lang][assumed]
            total = n
            marker = "**" if true_lang == assumed else ""
            cells.append(f"{marker}{domains / n:.1%}{marker}" if n else "—")
        out.append(f"| {true_lang} | " + " | ".join(cells) + f" | {total} |")
    out.append("")
    dom_ok = sum(results[lang][lang][1] for lang in LANGS)
    dom_bad = sum(results[t][a][1] for t in LANGS for a in LANGS if t != a)
    dom_ok_n = sum(results[lang][lang][2] for lang in LANGS)
    dom_bad_n = sum(results[t][a][2] for t in LANGS for a in LANGS if t != a)
    if dom_ok_n and dom_bad_n:
        out.append(
            f"**Domínio com idioma certo: {dom_ok / dom_ok_n:.1%}** · "
            f"**com idioma errado: {dom_bad / dom_bad_n:.1%}** · "
            f"queda de **{100 * (dom_ok / dom_ok_n - dom_bad / dom_bad_n):.1f} pontos**."
        )
    out.append("")

    correct = sum(results[lang][lang][0] for lang in LANGS)
    correct_n = sum(results[lang][lang][2] for lang in LANGS)
    wrong = sum(
        results[true][assumed][0] for true in LANGS for assumed in LANGS if true != assumed
    )
    wrong_n = sum(
        results[true][assumed][2] for true in LANGS for assumed in LANGS if true != assumed
    )
    if correct_n and wrong_n:
        out.append(
            f"**Idioma certo: {correct / correct_n:.1%}** (n={correct_n}) · "
            f"**idioma errado: {wrong / wrong_n:.1%}** (n={wrong_n}) · "
            f"queda de **{100 * (correct / correct_n - wrong / wrong_n):.1f} pontos**."
        )
    out.append("")
    out.append(
        "Ressalva: o pior caso de produção não é um sorteio uniforme entre idiomas errados. O "
        "default é `pt-BR`, então a coluna `pt` é a que um usuário sem preferência salva recebe, "
        "qualquer que seja o idioma do currículo dele."
    )
    text = "\n".join(out)
    print(text)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text + "\n", encoding="utf-8")
    print(f"\nwrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
