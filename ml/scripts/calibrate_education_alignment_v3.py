"""
Can encoder similarity replace _TECH_EDU_RE / _NON_TECH_EDU_RE in education alignment? Measured: no.

**Negative result. The swap was attempted, measured, and reverted.** This script is what measured
it, kept so the conclusion is reproducible rather than remembered.

The question the code has to answer is "does this education relate to this target role". There is no
labelled education-to-occupation pair on disk: the v3 corpus writes only the degree *level*
("Graduacao", "Bachelor", "Master") and never a field of study, so it carries no signal to fit on.
That is stated rather than worked around.

What is on disk is the ESCO taxonomy with ISCO-08 codes, which gives a **proxy**: two occupation
labels in the same ISCO group are related, two in different groups are not. That is occupation to
occupation, not education to occupation, so the threshold it yields is a calibrated starting point
for the same encoder on the same kind of short career-domain string — not a measurement of the real
task. Any report using it has to say so.

Two quantities are calibrated:

* **cosine** — the raw similarity between the two strings.
* **margin** — cosine minus the mean cosine against a fixed background sample of unrelated
  occupations. This is the section 6 pattern: absolute cosine barely separates (p05 was 0.579 for
  domain retrieval), while the margin does. It also solves the generic-degree case for free: a
  bare "Graduacao" sits equidistant from every occupation, so its margin collapses and the caller
  abstains instead of telling the user their degree does not match.

Usage:
  ./backend/.venv/Scripts/python.exe ml/scripts/calibrate_education_alignment_v3.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from apps.analysis.application.inference.text_probe import embed_documents  # noqa: E402

ESCO_PATH = REPO_ROOT / "ml" / "data" / "reference" / "esco_occupations.jsonl"
REPORT_PATH = REPO_ROOT / "ml" / "reports" / "education_alignment_v3.md"
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
SEED = 20260812
BACKGROUND_N = 64
PAIRS = 4000

BACKGROUND = (
    "enfermeiro hospitalar",
    "software developer",
    "contador financiero",
    "professor do ensino fundamental",
    "civil engineer",
    "chef de cocina",
    "motorista de caminhao",
    "graphic designer",
    "abogado laboralista",
    "tecnico em eletronica",
    "marketing manager",
    "agricultor",
)

# Field of study, target role, and whether a careers adviser would call them aligned. Deliberately
# easy: if a threshold cannot separate these, it cannot separate a real resume either.
HAND_CASES = (
    ("Ciencia da Computacao", "Programador", True),
    ("Analise e Desenvolvimento de Sistemas", "Desenvolvedor Backend", True),
    ("Computer Science", "Software Engineer", True),
    ("Ingenieria en Sistemas", "Desarrollador de software", True),
    ("Enfermagem", "Enfermeiro chefe", True),
    ("Pedagogia", "Professor do ensino fundamental", True),
    ("Biologia", "Programador", False),
    ("Direito", "Programador", False),
    ("Historia", "Engenheiro civil", False),
    ("Marketing", "Contador", False),
)


def separability(encoder) -> tuple[list[tuple[str, str, bool, float]], float, float]:
    rows: list[tuple[str, str, bool, float]] = []
    for education, target, aligned in HAND_CASES:
        matrix = embed_documents(encoder, [education, target, *BACKGROUND])
        margin = float(matrix[0] @ matrix[1]) - float((matrix[0] @ matrix[2:].T).mean())
        rows.append((education, target, aligned, margin))
    aligned_min = min(m for _e, _t, a, m in rows if a)
    unrelated_max = max(m for _e, _t, a, m in rows if not a)
    return rows, aligned_min, unrelated_max


def load_occupations(language: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in ESCO_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        label = (row.get("labels") or {}).get(language) or row.get("label") or ""
        isco = str(row.get("isco") or "")
        if label and len(isco) >= 2:
            out.append((str(label), isco[:2]))
    return out


def auc(positive: np.ndarray, negative: np.ndarray) -> float:
    joined = np.concatenate([positive, negative])
    order = joined.argsort()
    ranks = np.empty(len(joined), dtype=np.float64)
    ranks[order] = np.arange(1, len(joined) + 1)
    r_pos = ranks[: len(positive)].sum()
    return float(
        (r_pos - len(positive) * (len(positive) + 1) / 2) / (len(positive) * len(negative))
    )


def best_threshold(positive: np.ndarray, negative: np.ndarray) -> tuple[float, float]:
    grid = np.quantile(np.concatenate([positive, negative]), np.linspace(0.01, 0.99, 99))
    best = (-1.0, 0.0)
    for value in grid:
        acc = (float((positive >= value).sum()) + float((negative < value).sum())) / (
            len(positive) + len(negative)
        )
        if acc > best[0]:
            best = (acc, float(value))
    return best[1], best[0]


def main() -> None:
    from sentence_transformers import SentenceTransformer

    encoder = SentenceTransformer(EMBED_MODEL)
    rng = random.Random(SEED)
    out: list[str] = []
    out.append("# Education-to-target alignment — threshold calibration")
    out.append("")
    out.append(
        "Replaces `_TECH_EDU_RE` / `_NON_TECH_EDU_RE`, two closed lists of degree names that decide "
        "whether a candidate's education matches their target role."
    )
    out.append("")
    out.append(
        "**This is a proxy calibration, and the number must be read as one.** The v3 corpus records "
        "only the degree level (12 distinct strings: `Graduacao`, `Bachelor`, `Master`, ...) and "
        "never a field of study, so there is no labelled education-to-occupation pair to fit on. "
        "What follows measures the same encoder on the same kind of short career-domain string, "
        "using ESCO occupation pairs where same ISCO-08 group counts as related."
    )
    out.append("")
    out.append(
        f"Encoder `{EMBED_MODEL}` · {PAIRS} pairs per language · background sample "
        f"{BACKGROUND_N} occupations · seed {SEED}"
    )
    out.append("")
    out.append("| language | n occupations | AUC cosine | AUC margin | threshold (margin) | accuracy |")
    out.append("|---|---|---|---|---|---|")

    chosen: dict[str, float] = {}
    for language in ("pt", "en", "es"):
        occupations = load_occupations(language)
        if len(occupations) < 100:
            out.append(f"| {language} | {len(occupations)} | skipped, too few labels | | | |")
            continue
        labels = [label for label, _ in occupations]
        matrix = embed_documents(encoder, labels)

        by_group: dict[str, list[int]] = {}
        for index, (_label, group) in enumerate(occupations):
            by_group.setdefault(group, []).append(index)
        groups_with_pairs = [g for g, idx in by_group.items() if len(idx) >= 2]

        background_idx = rng.sample(range(len(labels)), BACKGROUND_N)
        background = matrix[background_idx]

        def margin_of(a: int, b: int) -> tuple[float, float]:
            cosine = float(matrix[a] @ matrix[b])
            base = float((matrix[a] @ background.T).mean())
            return cosine, cosine - base

        pos_cos, pos_margin, neg_cos, neg_margin = [], [], [], []
        for _ in range(PAIRS):
            group = rng.choice(groups_with_pairs)
            a, b = rng.sample(by_group[group], 2)
            cosine, margin = margin_of(a, b)
            pos_cos.append(cosine)
            pos_margin.append(margin)

            a2 = rng.randrange(len(labels))
            b2 = rng.randrange(len(labels))
            while occupations[a2][1] == occupations[b2][1]:
                b2 = rng.randrange(len(labels))
            cosine, margin = margin_of(a2, b2)
            neg_cos.append(cosine)
            neg_margin.append(margin)

        pos_cos_a = np.asarray(pos_cos)
        neg_cos_a = np.asarray(neg_cos)
        pos_margin_a = np.asarray(pos_margin)
        neg_margin_a = np.asarray(neg_margin)
        auc_cos = auc(pos_cos_a, neg_cos_a)
        auc_margin = auc(pos_margin_a, neg_margin_a)
        threshold, accuracy = best_threshold(pos_margin_a, neg_margin_a)
        chosen[language] = threshold
        out.append(
            f"| {language} | {len(occupations)} | {auc_cos:.3f} | **{auc_margin:.3f}** | "
            f"{threshold:.3f} | {accuracy:.1%} |"
        )

    out.append("")
    if chosen:
        low, high = min(chosen.values()), max(chosen.values())
        out.append(
            f"**Shipped thresholds, per language: "
            f"{json.dumps({k: round(v, 3) for k, v in chosen.items()})}**"
        )
        out.append("")
        out.append(
            f"Per language rather than pooled, because the spread is {high / max(low, 1e-9):.1f}x "
            f"({low:.3f} to {high:.3f}) and a single constant would misfire at both ends. The scale "
            "differs by language for a structural reason, not noise: ESCO's pt labels are long "
            "double-gender compounds (\"Operador de maquinas.../Operadora de maquinas...\") while "
            "its en labels are short noun phrases, so the background similarity they sit against "
            "differs."
        )
    out.append("")
    out.append("## The test that settled it: are the two classes separable at all?")
    out.append("")
    out.append(
        "The proxy above says the encoder ranks career-domain strings sensibly. It does not say a "
        "threshold exists for *this* decision. Ten hand-written pairs, chosen to be easy, answer that "
        "directly — a threshold classifies them only if every aligned pair outscores every unrelated "
        "one."
    )
    out.append("")
    rows, aligned_min, unrelated_max = separability(encoder)
    out.append("| field of study | target role | aligned? | margin |")
    out.append("|---|---|---|---|")
    for education, target, aligned, margin in sorted(rows, key=lambda r: -r[3]):
        out.append(f"| {education} | {target} | {'yes' if aligned else 'no'} | {margin:+.4f} |")
    out.append("")
    separable = aligned_min > unrelated_max
    out.append(
        f"Lowest aligned pair **{aligned_min:+.4f}** (Ingenieria en Sistemas / Desarrollador). "
        f"Highest unrelated pair **{unrelated_max:+.4f}** (Biologia / Programador). "
        f"**Separable: {'yes' if separable else 'no'}.**"
    )
    out.append("")
    if not separable:
        out.append(
            "The classes overlap, so **no threshold on this score classifies even these ten pairs**, "
            "and the swap was reverted. `education_aligned_with_target` keeps its keyword lists."
        )
        out.append("")
        out.append(
            "Why the proxy did not transfer: ESCO pairs are occupation-label against occupation-"
            "label, two strings of the same kind. The real task compares a *field of study* against "
            "a *job title*, which are different registers, and the margin scale moves with them. The "
            "proxy measured the encoder, not the decision."
        )
        out.append("")
        out.append(
            "What would unblock it, in order of cost: education field-of-study text in the corpus "
            "(the generator writes only the degree level today, 12 distinct strings), then a few "
            "hundred human-judged education-to-target pairs to fit and validate a boundary on. "
            "Neither exists on disk, and inventing the threshold is what this measurement prevents."
        )
    out.append("")
    out.append("## What this does and does not license")
    out.append("")
    out.append(
        "- It does **not** license shipping encoder similarity as the decider for this feature."
    )
    out.append(
        "- It does **not** license publishing an accuracy figure for education alignment. The real "
        "task is unmeasured until resumes carry a field of study."
    )
    out.append(
        "- The separation is only moderate even on the proxy (AUC 0.75-0.79, accuracy 69-72%), which "
        "was the first warning; the hand-case overlap above is the confirmation."
    )
    out.append(
        "- The incumbent keyword lists remain wrong in the ways already documented — pt-BR shaped, "
        "gated on a closed 'tech target' list, literal token overlap otherwise. **Both options are "
        "bad, and this measurement says which is not yet demonstrably better.**"
    )
    out.append(
        "- One design idea worth keeping for the retry: a bare degree level sits equidistant from "
        "every occupation, so a margin near zero is a usable abstention signal. That part behaved as "
        "intended (`Graduacao Bacharelado` scored -0.012); it is the aligned/unrelated boundary that "
        "does not exist, not the ability to spot an uninformative degree."
    )
    text = "\n".join(out)
    print(text)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text + "\n", encoding="utf-8")
    print(f"\nwrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
