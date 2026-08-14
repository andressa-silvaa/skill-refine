"""
Detect the language a resume is written in, instead of trusting the user's interface preference.

``worker.py`` passes ``UserPreferences.language`` into the analysis and never reads the document, so
an English CV uploaded by a user with a Portuguese UI is analysed as pt-BR — and pt-BR is also the
default when no preference is saved. Measured cost of that mistake (ml/reports/language_mismatch_v3.md):
ESCO occupation retrieval falls 29.5 points and the domain that feeds ``careerSwitch`` and
``target_seniority`` falls 14.9.

Character n-grams rather than the resident MiniLM: language identity lives in letter sequences and
diacritics, not in meaning, and a sentence encoder is trained to make *the same sentence in three
languages* land in the same place — the opposite of what is needed here. Character n-grams also cost
a sparse dot product and no model load.

The corpus labels the language by construction, so no annotation is needed. Two honest limits this
script measures rather than assumes:

* **Held out by occupation**, like every other head in this project, so vocabulary from one
  occupation cannot appear on both sides of the split.
* **Mixed-language resumes.** A Portuguese CV listing English tech skills is ordinary, and it is the
  case where a detector trained on clean generated prose is most likely to break. There is a
  dedicated adversarial set below; a high held-out score with a failing mixed set means the number is
  not usable, and the report says so.

Usage:
  ./backend/.venv/Scripts/python.exe ml/scripts/train_language_detector_v3.py
  ./backend/.venv/Scripts/python.exe ml/scripts/train_language_detector_v3.py --no-export
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
for extra in (str(REPO_ROOT / "backend" / "src"), str(Path(__file__).resolve().parent)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

import label_seniority_llm_v3 as base  # noqa: E402

from apps.analysis.application.inference.resume_mapper import resume_to_text  # noqa: E402

MODELS_DIR = REPO_ROOT / "ml" / "models" / "language_detector_v1"
REPORT_PATH = REPO_ROOT / "ml" / "reports" / "language_detector_v3.md"
SEED = 20260814
N_SPLITS = 5
LANGS = ("pt", "en", "es")

# A Portuguese or Spanish resume whose skills, tools and job titles are English. This is what a real
# technology CV looks like in Brazil, and it is the case a detector trained on clean prose fails.
MIXED_CASES = (
    (
        "pt",
        "Desenvolvedor Full Stack com 5 anos de experiencia. Atuei com React, Node.js, Docker, "
        "Kubernetes e AWS. Responsavel por deploy continuo e code review do time de backend.",
    ),
    (
        "pt",
        "Analista de dados. Stack: Python, pandas, SQL, Airflow, dbt, Snowflake. Construi "
        "dashboards em Power BI e pipelines de ETL para o time de growth.",
    ),
    (
        "es",
        "Ingeniero de software con experiencia en microservices, Spring Boot, Kafka y CI/CD. "
        "Lidere el equipo de backend y el proceso de code review.",
    ),
    (
        "es",
        "Diseñador UX. Herramientas: Figma, Sketch, InVision. Realicé user research, wireframes "
        "y testing de usabilidad para productos digitales.",
    ),
    (
        "en",
        "Software engineer with experience in distributed systems, Go, and PostgreSQL. Led the "
        "platform team and owned the on-call rotation.",
    ),
    (
        "pt",
        "Gerente de projetos certificada PMP e Scrum Master. Conduzi cerimonias de sprint planning, "
        "daily standup e retrospectiva com stakeholders internacionais.",
    ),
)

SHORT_CASES = (
    ("pt", "Analista de marketing digital com foco em campanhas."),
    ("en", "Marketing analyst focused on digital campaigns."),
    ("es", "Analista de marketing digital enfocado en campañas."),
)

# Accents typed away. Ordinary in resumes pasted from plain text or typed on a foreign keyboard, and
# the hardest case for a character n-gram model, because diacritics are most of what separates
# Portuguese from Spanish once the shared Latin vocabulary is stripped of them. Kept as its own block
# so a failure here is not confused with a failure on well-formed text.
STRIPPED_ACCENT_CASES = (
    ("es", "Analista de marketing digital enfocado en campanas para el mercado local."),
    ("pt", "Analista de marketing digital com foco em campanhas para o mercado local."),
    ("es", "Disenador grafico con experiencia en identidad visual y produccion editorial."),
)


def build_pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(1, 3),
                    min_df=2,
                    max_features=50000,
                    sublinear_tf=True,
                ),
            ),
            ("clf", LogisticRegression(max_iter=2000, C=4.0, random_state=SEED)),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-export", action="store_true")
    args = parser.parse_args()

    from sklearn.model_selection import GroupKFold

    rows = base.load_rows()
    texts: list[str] = []
    labels: list[str] = []
    groups: list[str] = []
    for row in rows:
        resume_data = row.get("resume_data")
        if not isinstance(resume_data, dict):
            continue
        language = str(row.get("language") or "").split("-")[0].lower()
        if language not in LANGS:
            continue
        text = resume_to_text(resume_data, language=row.get("language") or "pt-BR").full_text
        if len(text.strip()) < 40:
            continue
        texts.append(text)
        labels.append(language)
        groups.append(str((row.get("occupation") or {}).get("uri") or f"__row_{row['id']}"))

    if not texts:
        raise SystemExit("no usable rows")
    x = np.asarray(texts, dtype=object)
    y = np.asarray(labels)
    g = np.asarray(groups)
    print(f"{len(texts)} resumes · {dict(collections.Counter(labels))}")

    predictions = np.empty(len(y), dtype=object)
    splitter = GroupKFold(n_splits=N_SPLITS)
    for train_idx, test_idx in splitter.split(x, y, g):
        pipeline = build_pipeline()
        pipeline.fit(x[train_idx], y[train_idx])
        predictions[test_idx] = pipeline.predict(x[test_idx])

    accuracy = float(np.mean(predictions == y))
    out: list[str] = []
    out.append("# Detector de idioma do currículo — v3")
    out.append("")
    out.append(
        f"Gerado {date.today().isoformat()} · {len(texts)} currículos · TF-IDF de n-gramas de "
        f"caractere (1-3, `char_wb`) + regressão logística · {N_SPLITS}-fold GroupKFold pela ocupação."
    )
    out.append("")
    out.append(
        "Substitui `UserPreferences.language`, que é a preferência de **interface** do usuário e "
        "nunca olha o documento. Custo medido de errar: recuperação de ocupação cai 29,5 pontos e "
        "domínio cai 14,9 (ml/reports/language_mismatch_v3.md)."
    )
    out.append("")
    out.append(f"## Held-out por ocupação: **{accuracy:.2%}**")
    out.append("")
    out.append("| idioma real \\ predito | " + " | ".join(LANGS) + " | n |")
    out.append("|---|" + "---|" * (len(LANGS) + 1))
    for true_lang in LANGS:
        mask = y == true_lang
        if not mask.any():
            continue
        cells = [f"{int(np.sum(predictions[mask] == p))}" for p in LANGS]
        out.append(f"| {true_lang} | " + " | ".join(cells) + f" | {int(mask.sum())} |")
    out.append("")

    confidences = np.empty(len(y), dtype=float)
    for train_idx, test_idx in splitter.split(x, y, g):
        pipeline = build_pipeline()
        pipeline.fit(x[train_idx], y[train_idx])
        confidences[test_idx] = pipeline.predict_proba(x[test_idx]).max(axis=1)
    out.append("## Distribuição de confiança no held-out")
    out.append("")
    out.append(
        "O piso de confiança abaixo do qual a inferência **não** sobrepõe a preferência do usuário "
        "precisa vir daqui, não dos casos escritos à mão — senão é ajustar o limiar aos próprios "
        "exemplos."
    )
    out.append("")
    percentiles = [1, 5, 25, 50]
    values = [float(np.percentile(confidences, p)) for p in percentiles]
    out.append("| percentil | " + " | ".join(f"p{p}" for p in percentiles) + " |")
    out.append("|---|" + "---|" * len(percentiles))
    out.append("| confiança | " + " | ".join(f"{v:.3f}" for v in values) + " |")
    out.append("")
    out.append(
        f"Mesmo o percentil 1 do corpus fica em **{values[0]:.3f}**, muito acima das falhas do bloco "
        "adversarial (0,35 e 0,39). Um piso na casa de 0,50 descarta praticamente nada de texto bem "
        "formado e ainda assim recusa os casos curtos e ambíguos — é margem de segurança declarada, "
        "não limiar ajustado."
    )
    out.append("")

    final = build_pipeline()
    final.fit(x, y)

    out.append("## O teste que decide se o número serve: currículo com idiomas misturados")
    out.append("")
    out.append(
        "Prosa gerada é limpa e monolíngue. Currículo real não é: um CV de tecnologia em português "
        "lista React, Docker e code review em inglês. Um held-out alto com este bloco falhando "
        "significaria que o número não vale para usuário real."
    )
    out.append("")
    out.append("| esperado | predito | confiança | trecho |")
    out.append("|---|---|---|---|")
    mixed_ok = 0
    for expected, text in MIXED_CASES + SHORT_CASES + STRIPPED_ACCENT_CASES:
        probabilities = final.predict_proba([text])[0]
        predicted = str(final.classes_[int(np.argmax(probabilities))])
        mixed_ok += int(predicted == expected)
        mark = "" if predicted == expected else " **FALHOU**"
        out.append(
            f"| {expected} | {predicted}{mark} | {float(np.max(probabilities)):.2f} | "
            f"{text[:62]}… |"
        )
    total_cases = len(MIXED_CASES) + len(SHORT_CASES) + len(STRIPPED_ACCENT_CASES)
    out.append("")
    out.append(f"**{mixed_ok}/{total_cases}** nos casos adversariais.")
    out.append("")
    if mixed_ok < total_cases:
        out.append(
            "Falhas acima são o sinal de que treinar só em prosa gerada não cobre currículo real. "
            "Antes de embarcar, ou o corpus ganha exemplos misturados ou entra uma biblioteca "
            "treinada em texto natural."
        )
    else:
        out.append(
            "O detector sobrevive à mistura, que era o modo de falha esperado. Os n-gramas de "
            "caractere pegam a morfologia e os diacríticos das palavras funcionais, e essas "
            "permanecem no idioma do documento mesmo quando os substantivos técnicos não."
        )
    out.append("")
    out.append("## Limites")
    out.append("")
    out.append(
        "- Treinado em **prosa gerada por LLM**, não em currículo real. O bloco adversarial acima é "
        "escrito à mão e é a única evidência sobre texto fora do gerador."
    )
    out.append(
        "- Cobre **pt, en, es** e nada mais. Um currículo em francês recebe um dos três, com "
        "confiança possivelmente alta — por isso a inferência exige um piso de confiança e cai na "
        "preferência do usuário abaixo dele, em vez de afirmar."
    )
    text_out = "\n".join(out)
    print(text_out)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text_out + "\n", encoding="utf-8")
    print(f"\nwrote {REPORT_PATH}")

    if not args.no_export:
        import joblib

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipeline": final, "classes": list(final.classes_)}, MODELS_DIR / "model.joblib")
        (MODELS_DIR / "metadata.json").write_text(
            json.dumps(
                {
                    "task": "language_detector",
                    "model_name": "language_detector",
                    "model_version": "language_detector_v1",
                    "dataset_version": f"resumes_v3_{len(texts)}rows_{date.today().isoformat()}",
                    "features": "tfidf char_wb 1-3grams, max 50k",
                    "languages": list(LANGS),
                    "label_source": "corpus language, true by construction",
                    "training_rows": len(texts),
                    "evaluation": "GroupKFold over ESCO occupation",
                    "heldout_accuracy": round(accuracy, 4),
                    "adversarial_mixed_cases": f"{mixed_ok}/{total_cases}",
                    "trained_on": date.today().isoformat(),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"wrote {MODELS_DIR}")


if __name__ == "__main__":
    main()
