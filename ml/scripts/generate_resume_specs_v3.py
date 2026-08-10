"""
Phase 1a of the v3 synthetic corpus: structural resume SPECS (no prose, no API calls).

Why specs are separate from prose: the numeric distribution is what broke the v2 model
(summary_char_count spanned 30-61 chars in training vs 183-360 in real resumes, putting real
input 25 sigma out and making the classifier emit a single class). Structure therefore stays
programmatic and inspectable here, while phase 1b (write_resume_prose_v3.py) asks an LLM to
write natural bullets/summary for the occupation and scope level each spec declares.

Design invariants, each aimed at a shortcut the model must not learn:
  - occupation: sampled uniformly from ~1.7k ESCO occupations, independent of band. High
    cardinality means <2 examples per occupation, so there is no per-domain statistic to
    memorise and the model is forced onto scope/tenure/autonomy signals.
  - language: sampled independently of band, so "English" cannot imply a seniority.
  - summary length: uniform 150-400 chars regardless of band, so the feature carries zero
    label information and can neither be exploited nor blow up out of distribution.
  - job title: ~35% carry no seniority modifier at all, and a share are deliberately
    mismatched (inflated at short tenure, modest at long tenure), so the title alone
    cannot be read off as the answer.
  - band_target is the GENERATION target, not the training label. The label comes from an
    independent LLM pass reading only the finished text, which is what breaks the
    circularity of v2 (whose labels came from a formula over these same numbers).

Output: ml/data/raw/resumes_v3/specs.jsonl

Usage (from repo root):
  python ml/scripts/generate_resume_specs_v3.py --count 2000
  python ml/scripts/generate_resume_specs_v3.py --count 300 --parallel 60 --seed 7
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import date
from pathlib import Path
from typing import Any

ML_ROOT = Path(__file__).resolve().parents[1]
ESCO_PATH = ML_ROOT / "data" / "reference" / "esco_occupations.jsonl"
OUT_DIR = ML_ROOT / "data" / "raw" / "resumes_v3"

BANDS = ("intern", "junior", "mid", "senior")
LANGS = ("pt-BR", "en-US", "es-ES")
LANG_WEIGHTS = (0.50, 0.25, 0.25)

TODAY = date(2026, 8, 1)

TOTAL_MONTHS_RANGE = {
    "intern": (2, 14),
    "junior": (10, 30),
    "mid": (24, 72),
    "senior": (60, 260),
}

N_EXPERIENCES_WEIGHTS = {
    "intern": {1: 0.70, 2: 0.30},
    "junior": {1: 0.45, 2: 0.40, 3: 0.15},
    "mid": {1: 0.20, 2: 0.35, 3: 0.30, 4: 0.15},
    "senior": {1: 0.20, 2: 0.25, 3: 0.25, 4: 0.15, 5: 0.10, 6: 0.05},
}

LEADERSHIP_PROB = {"intern": 0.0, "junior": 0.08, "mid": 0.45, "senior": 1.0}

SUMMARY_SENTENCES_RANGE = (1, 4)

# Resume quality is sampled independently of the seniority band, because a senior can write a
# terrible resume and an intern an excellent one. Any correlation here would let a quality model
# read seniority off its own target and vice versa.
QUALITY_LEVELS = ("poor", "fair", "good")
NO_SUMMARY_PROB = 0.08

TOTAL_BULLETS_RANGE = (1, 18)
MAX_BULLETS_PER_JOB = 8

HAS_LINKS_PROB = 0.55
HAS_EDUCATION_PROB = 0.90
LINK_FIELDS = ("linkedin", "github", "portfolio", "website")

TITLE_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "pt-BR": {
        "intern": ("{occ} (Estágio)", "Estagiário — {occ}", "{occ} (Trainee)"),
        "junior": ("{occ} Júnior", "{occ} Jr.", "{occ} I"),
        "mid": ("{occ} Pleno", "{occ}", "{occ} II"),
        "senior": ("{occ} Sênior", "{occ} Especialista", "{occ} Líder", "Líder de Equipe — {occ}"),
    },
    "en-US": {
        "intern": ("{occ} Intern", "{occ} (Internship)", "{occ} Trainee"),
        "junior": ("Junior {occ}", "Entry-level {occ}", "Associate {occ}"),
        "mid": ("{occ}", "Mid-level {occ}", "{occ} II"),
        "senior": ("Senior {occ}", "Lead {occ}", "Principal {occ}", "Staff {occ}"),
    },
    "es-ES": {
        "intern": ("{occ} (Prácticas)", "Becario — {occ}", "{occ} en prácticas"),
        "junior": ("{occ} Junior", "{occ} I"),
        "mid": ("{occ}", "{occ} Semi-Senior"),
        "senior": ("{occ} Senior", "{occ} Principal", "Jefe de Equipo — {occ}"),
    },
}

LOWERCASE_PARTICLES = {
    "de", "da", "do", "das", "dos", "e", "em", "para", "a", "o",
    "del", "la", "las", "los", "y", "en", "of", "and", "the", "for",
}

UNMARKED_TITLE_PROB = 0.35
TITLE_MISMATCH_PROB = 0.15

COMPANY_STEMS = (
    "Aurora", "Boreal", "Cedro", "Delta", "Elipse", "Fonte", "Granada", "Horizonte",
    "Íbis", "Jade", "Kappa", "Lumen", "Meridiano", "Nova", "Orion", "Pauta", "Quartzo",
    "Ravena", "Solar", "Tramo", "Umbra", "Vega", "Zênite", "Âncora", "Bússola", "Cristal",
)
COMPANY_SUFFIX = {
    "pt-BR": ("Ltda", "S.A.", "Serviços", "Group", "do Brasil"),
    "en-US": ("Inc.", "LLC", "Group", "Partners", "Solutions"),
    "es-ES": ("S.L.", "S.A.", "Grupo", "Servicios", "Ibérica"),
}

EDUCATION_POOL = {
    "pt-BR": (
        ("Universidade Federal", "Graduação", "Bacharelado"),
        ("Instituto Técnico", "Curso Técnico", "Técnico"),
        ("Centro Universitário", "Graduação em andamento", "Cursando"),
        ("Universidade Estadual", "Pós-graduação", "Especialização"),
    ),
    "en-US": (
        ("State University", "Bachelor", "BSc"),
        ("Community College", "Associate Degree", "AA"),
        ("Technical Institute", "Diploma", "Diploma"),
        ("University", "Master", "MSc"),
    ),
    "es-ES": (
        ("Universidad Nacional", "Grado", "Licenciatura"),
        ("Instituto Técnico", "Ciclo Formativo", "Técnico"),
        ("Universidad Autónoma", "Grado en curso", "Cursando"),
        ("Universidad Politécnica", "Máster", "Máster"),
    ),
}

SCOPE_LEVELS = {
    "intern": "assist",
    "junior": "execute",
    "mid": "own",
    "senior": "lead",
}


def load_occupations() -> list[dict[str, Any]]:
    if not ESCO_PATH.exists():
        raise SystemExit(
            f"missing {ESCO_PATH}\nrun first: python ml/scripts/fetch_esco_occupations.py"
        )
    rows = []
    for line in ESCO_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        raise SystemExit(f"{ESCO_PATH} is empty")
    return rows


def _title_case(label: str) -> str:
    words = label.split()
    out = []
    for i, w in enumerate(words):
        if len(w) > 1 and w.isupper():
            out.append(w)
            continue
        low = w.lower()
        if i > 0 and low in LOWERCASE_PARTICLES:
            out.append(low)
        else:
            out.append(low[0].upper() + low[1:] if low else w)
    return " ".join(out)


def occupation_label(occ: dict[str, Any], language: str, rng: random.Random) -> str:
    key = {"pt-BR": "pt", "en-US": "en", "es-ES": "es"}[language]
    raw = str((occ.get("labels") or {}).get(key) or "").strip()
    variants = [v.strip() for v in raw.split("/") if v.strip()]
    label = rng.choice(variants) if variants else raw
    return _title_case(label)


def _weighted_choice(weights: dict[int, float], rng: random.Random) -> int:
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys], k=1)[0]


def _split_months(total: int, n: int, rng: random.Random, *, min_span: int) -> list[int]:
    """Split total tenure into n spans, each >= min_span, without slicing off 2-month stubs."""
    if n <= 1 or total < min_span * 2:
        return [total]
    n = min(n, max(1, total // min_span))
    if n <= 1:
        return [total]
    slack = total - n * min_span
    weights = [rng.random() for _ in range(n)]
    wsum = sum(weights) or 1.0
    parts = [min_span + int(slack * w / wsum) for w in weights]
    parts[0] += total - sum(parts)
    return parts


def _distribute_bullets(n_exp: int, rng: random.Random) -> list[int]:
    """
    Total bullet budget is drawn independently of the band, then spread across jobs.

    Sampling per job instead would let band leak in through experiences_count (which does
    correlate with band), rebuilding the very count-based shortcut that mislabelled long-tenure
    single-job seniors. Independent totals also produce terse seniors and verbose interns.
    """
    total = max(n_exp, rng.randint(*TOTAL_BULLETS_RANGE))
    counts = [1] * n_exp
    for _ in range(total - n_exp):
        candidates = [i for i, c in enumerate(counts) if c < MAX_BULLETS_PER_JOB]
        if not candidates:
            break
        counts[rng.choice(candidates)] += 1
    return counts


def _iso(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _shift_months(d: date, months: int) -> date:
    total = (d.year * 12 + d.month - 1) - months
    return date(total // 12, total % 12 + 1, 1)


def build_title(occ_label: str, band: str, language: str, rng: random.Random) -> tuple[str, str]:
    """Returns (title, marking) where marking is unmarked | matched | mismatched."""
    if rng.random() < UNMARKED_TITLE_PROB:
        return occ_label, "unmarked"
    if rng.random() < TITLE_MISMATCH_PROB:
        i = BANDS.index(band)
        adjacent = [BANDS[j] for j in (i - 1, i + 1) if 0 <= j < len(BANDS)]
        shown = rng.choice(adjacent)
        pattern = rng.choice(TITLE_PATTERNS[language][shown])
        return pattern.format(occ=occ_label), "mismatched"
    pattern = rng.choice(TITLE_PATTERNS[language][band])
    return pattern.format(occ=occ_label), "matched"


def generate_spec(
    occ: dict[str, Any],
    band: str,
    language: str,
    rng: random.Random,
    *,
    parallel_group: str | None = None,
) -> dict[str, Any]:
    occ_label = occupation_label(occ, language, rng)
    lo, hi = TOTAL_MONTHS_RANGE[band]
    total_months = rng.randint(lo, hi)
    n_exp = _weighted_choice(N_EXPERIENCES_WEIGHTS[band], rng)
    min_span = 3 if band == "intern" else 8
    spans = _split_months(total_months, n_exp, rng, min_span=min_span)
    n_exp = len(spans)

    has_current = rng.random() < 0.75
    bullet_counts = _distribute_bullets(n_exp, rng)
    experiences: list[dict[str, Any]] = []
    cursor = TODAY
    for idx, span in enumerate(spans):
        is_current = bool(idx == 0 and has_current)
        end = cursor
        start = _shift_months(end, span)
        title, marking = build_title(occ_label, band, language, rng)
        experiences.append(
            {
                "position": title,
                "title_marking": marking,
                "company": f"{rng.choice(COMPANY_STEMS)} {rng.choice(COMPANY_SUFFIX[language])}",
                "startDate": _iso(start),
                "endDate": None if is_current else _iso(end),
                "isCurrent": is_current,
                "n_bullets": bullet_counts[idx],
                "months": span,
                "scope_level": SCOPE_LEVELS[band] if idx == 0 else SCOPE_LEVELS[
                    BANDS[max(0, BANDS.index(band) - 1)]
                ],
            }
        )
        cursor = _shift_months(start, rng.randint(0, 4))

    institution, degree_kind, degree = rng.choice(EDUCATION_POOL[language])
    contact: dict[str, str] = {}
    if rng.random() < HAS_LINKS_PROB:
        for field in rng.sample(LINK_FIELDS, k=rng.randint(1, 2)):
            contact[field] = f"{field}.com/perfil-anon"
    return {
        "id": f"{rng.getrandbits(48):x}",
        "parallel_group": parallel_group,
        "language": language,
        "band_target": band,
        "occupation": {
            "uri": occ.get("uri"),
            "isco": occ.get("isco"),
            "isco_group": occ.get("isco_group"),
            "label": occ_label,
        },
        "summary_sentences": 0
        if rng.random() < NO_SUMMARY_PROB
        else rng.randint(*SUMMARY_SENTENCES_RANGE),
        "contact": contact,
        "has_education": rng.random() < HAS_EDUCATION_PROB,
        "wants_leadership_language": rng.random() < LEADERSHIP_PROB[band],
        "may_state_seniority": rng.random() < 0.20,
        "quality_target": rng.choice(QUALITY_LEVELS),
        "total_months_design": total_months,
        "experiences": experiences,
        "education": {"institution": institution, "course": degree_kind, "degree": degree},
        "n_skills": rng.randint(3, 12),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=2000)
    ap.add_argument("--parallel", type=int, default=120, help="specs rendered in all 3 languages")
    ap.add_argument("--seed", type=int, default=20260806)
    ap.add_argument("--out", default="specs.jsonl")
    ap.add_argument("--id-prefix", default="", help="keeps ids from colliding with an earlier batch")
    ap.add_argument(
        "--band-weights",
        default="",
        help="skew targets to rebalance measured LLM labels, e.g. intern=45,senior=35,junior=12,mid=8",
    )
    args = ap.parse_args()

    band_weights: dict[str, float] | None = None
    if args.band_weights.strip():
        band_weights = {}
        for part in args.band_weights.split(","):
            k, _, v = part.partition("=")
            if k.strip() in BANDS:
                band_weights[k.strip()] = float(v or 0)
        if not band_weights:
            band_weights = None

    rng = random.Random(args.seed)
    occupations = load_occupations()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / args.out

    specs: list[dict[str, Any]] = []

    prefix = args.id_prefix

    def pick_band(i: int) -> str:
        if band_weights:
            return rng.choices(list(band_weights), weights=list(band_weights.values()), k=1)[0]
        return BANDS[i % len(BANDS)]

    for i in range(args.parallel):
        occ = rng.choice(occupations)
        band = pick_band(i)
        group = f"{prefix}par{i:04d}"
        base_seed = rng.getrandbits(32)
        for language in LANGS:
            sub = random.Random(base_seed)
            spec = generate_spec(occ, band, language, sub, parallel_group=group)
            spec["id"] = f"{group}_{language}"
            specs.append(spec)

    remaining = max(0, args.count - len(specs))
    for i in range(remaining):
        occ = rng.choice(occupations)
        band = pick_band(i)
        language = rng.choices(LANGS, weights=LANG_WEIGHTS, k=1)[0]
        spec = generate_spec(occ, band, language, rng)
        spec["id"] = f"{prefix}gen{i:05d}"
        specs.append(spec)

    rng.shuffle(specs)
    with out_path.open("w", encoding="utf-8") as fh:
        for s in specs:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")

    from collections import Counter
    print(f"wrote {len(specs)} specs -> {out_path}")
    print("band_target:", dict(Counter(s["band_target"] for s in specs)))
    print("language:", dict(Counter(s["language"] for s in specs)))
    print("parallel groups:", len({s["parallel_group"] for s in specs if s["parallel_group"]}))
    print("distinct occupations:", len({s["occupation"]["uri"] for s in specs}))
    print("title marking:", dict(Counter(
        e["title_marking"] for s in specs for e in s["experiences"]
    )))


if __name__ == "__main__":
    main()
