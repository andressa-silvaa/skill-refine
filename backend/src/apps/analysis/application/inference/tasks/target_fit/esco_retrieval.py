"""
Zero-shot occupation inference by semantic retrieval over the ESCO taxonomy.

The resume text and the ~1.7k ESCO occupation labels pass through the same multilingual
bi-encoder; the nearest labels are the predicted occupation, and the domain comes from the
ISCO-08 group of the winner. No training, no labels, and the reachable label space is the
official taxonomy instead of a hand-written keyword list, so an occupation nobody enumerated
is still classifiable.

Labels are embedded once per process and persisted under ml/data/reference/esco_embeddings so a
cold process pays a file read instead of ~1.7k encodings per language.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .isco_domains import domain_for_isco

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
# Alternative labels measured worse than preferred labels alone on the v3 corpus
# (domain 84.0% vs 85.5%, occupation top-1 63.1% vs 66.1%): they pull short queries toward
# whichever occupation happens to list the most synonyms.
DEFAULT_MAX_ALT_LABELS = 0
MAX_QUERY_CHARS = 1200
MIN_COSINE_FLOOR = 0.20
# Calibrated on 873 corpus resumes (see ml/scripts/eval_domain_inference_esco.py): domain accuracy
# by margin was 98% above 0.10, 90% between 0.05 and 0.10, and 35-62% below 0.05.
CONFIDENCE_HIGH_MARGIN = 0.10
CONFIDENCE_HIGH_COSINE = 0.55
CONFIDENCE_MEDIUM_MARGIN = 0.05
CONFIDENCE_MEDIUM_COSINE = 0.75

_SUPPORTED_LANGS = ("pt", "en", "es")

_lock = threading.Lock()
_index_cache: dict[str, "OccupationIndex | None"] = {}
_occupations_cache: dict[str, list[dict[str, Any]]] = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[8]


def default_occupations_path() -> Path:
    return _repo_root() / "ml" / "data" / "reference" / "esco_occupations.jsonl"


def default_cache_dir() -> Path:
    return _repo_root() / "ml" / "data" / "reference" / "esco_embeddings"


def lang_key(lang: str | None) -> str:
    lc = str(lang or "").strip().lower()
    for code in _SUPPORTED_LANGS:
        if lc.startswith(code):
            return code
    return "en"


@dataclass
class OccupationIndex:
    lang: str
    occupations: list[dict[str, Any]]
    matrix: Any
    row_to_occupation: Any


def _first_variant(label: str) -> str:
    """pt/es preferred labels carry gender variants split by '/': keep the first."""
    for chunk in str(label or "").split("/"):
        text = chunk.strip()
        if text:
            return text
    return ""


def _label_variants(row: dict[str, Any], lang: str, max_alt: int) -> list[str]:
    labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
    primary = _first_variant(labels.get(lang) or labels.get("en") or "")
    variants: list[str] = []
    seen: set[str] = set()
    if primary:
        variants.append(primary)
        seen.add(primary.casefold())
    alt_block = row.get("alt") if isinstance(row.get("alt"), dict) else {}
    for raw in alt_block.get(lang) or []:
        if len(variants) > max_alt:
            break
        text = _first_variant(raw)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            variants.append(text)
    return variants


def load_occupations(path: Path | str | None = None) -> list[dict[str, Any]]:
    source = Path(path) if path else default_occupations_path()
    key = str(source)
    with _lock:
        cached = _occupations_cache.get(key)
    if cached is not None:
        return cached
    rows: list[dict[str, Any]] = []
    try:
        with source.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                isco = str(row.get("isco") or "")
                rows.append(
                    {
                        "uri": str(row.get("uri") or ""),
                        "isco": isco,
                        "isco_group": str(row.get("isco_group") or ""),
                        "domain": domain_for_isco(isco),
                        "labels": row.get("labels") if isinstance(row.get("labels"), dict) else {},
                        "alt": row.get("alt") if isinstance(row.get("alt"), dict) else {},
                    }
                )
    except OSError as exc:
        logger.warning("esco: occupations file unreadable (%s): %s", source, exc)
        rows = []
    with _lock:
        _occupations_cache[key] = rows
    return rows


def _model_slug(model: Any, model_name: str) -> str:
    name = str(model_name or "").strip() or type(model).__name__
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in name.split("/")[-1])[:64]


def _fingerprint(texts: list[str]) -> str:
    digest = hashlib.sha1("\n".join(texts).encode("utf-8"))
    return digest.hexdigest()[:16]


def _cache_path(cache_dir: Path, slug: str, lang: str, max_alt: int) -> Path:
    return cache_dir / f"{slug}__{lang}__alt{max_alt}.npz"


def _load_cached_matrix(path: Path, fingerprint: str):
    try:
        import numpy as np
    except ImportError:
        return None
    if not path.exists():
        return None
    try:
        with np.load(path, allow_pickle=False) as blob:
            if str(blob["fingerprint"].item()) != fingerprint:
                return None
            return np.asarray(blob["matrix"], dtype=np.float32), np.asarray(blob["row_to_occupation"], dtype=np.int32)
    except Exception as exc:
        logger.warning("esco: embedding cache unusable (%s): %s", path, exc)
        return None


def _store_cached_matrix(path: Path, fingerprint: str, matrix, row_to_occupation) -> None:
    try:
        import numpy as np

        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            matrix=matrix,
            row_to_occupation=row_to_occupation,
            fingerprint=np.asarray(fingerprint),
        )
    except Exception as exc:
        logger.warning("esco: could not persist embedding cache (%s): %s", path, exc)


def _encode(model, texts: list[str]):
    import numpy as np

    emb = model.encode(
        texts,
        batch_size=64,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(emb, dtype=np.float32)


def get_occupation_index(
    model: Any,
    lang: str,
    *,
    occupations_path: Path | str | None = None,
    cache_dir: Path | str | None = None,
    max_alt_labels: int = DEFAULT_MAX_ALT_LABELS,
    model_name: str = "",
) -> OccupationIndex | None:
    if model is None:
        return None
    try:
        import numpy as np
    except ImportError:
        return None

    code = lang_key(lang)
    slug = _model_slug(model, model_name)
    cache_key = f"{slug}|{code}|{max_alt_labels}|{occupations_path or ''}"
    with _lock:
        if cache_key in _index_cache:
            return _index_cache[cache_key]

    occupations = load_occupations(occupations_path)
    if not occupations:
        with _lock:
            _index_cache[cache_key] = None
        return None

    texts: list[str] = []
    row_to_occupation: list[int] = []
    for idx, row in enumerate(occupations):
        for variant in _label_variants(row, code, max_alt_labels):
            texts.append(variant)
            row_to_occupation.append(idx)
    if not texts:
        with _lock:
            _index_cache[cache_key] = None
        return None

    fingerprint = _fingerprint(texts)
    directory = Path(cache_dir) if cache_dir else default_cache_dir()
    path = _cache_path(directory, slug, code, max_alt_labels)
    cached = _load_cached_matrix(path, fingerprint)
    if cached is not None and cached[0].shape[0] == len(texts) == cached[1].shape[0]:
        matrix, rows = cached
    else:
        matrix = _encode(model, texts)
        rows = np.asarray(row_to_occupation, dtype=np.int32)
        _store_cached_matrix(path, fingerprint, matrix, rows)
        logger.info("esco: embedded %d labels for %s", len(texts), code)

    index = OccupationIndex(
        lang=code,
        occupations=occupations,
        matrix=matrix,
        row_to_occupation=rows,
    )
    with _lock:
        _index_cache[cache_key] = index
    return index


_INDEX_OPTION_KEYS = frozenset({"occupations_path", "cache_dir", "max_alt_labels", "model_name"})


def warm_occupation_index(model: Any, lang: str, options: dict[str, Any] | None = None) -> bool:
    """Build (or read from disk) the label matrix ahead of the first request."""
    kwargs = {k: v for k, v in (options or {}).items() if k in _INDEX_OPTION_KEYS}
    return get_occupation_index(model, lang, **kwargs) is not None


def retrieve_occupations(
    model: Any,
    text: str,
    lang: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    index: OccupationIndex | None = None,
    **index_kwargs: Any,
) -> list[tuple[dict[str, Any], float]]:
    """Top-k ESCO occupations by cosine, scored by their best-matching label variant."""
    query = str(text or "").strip()[:MAX_QUERY_CHARS]
    if not query:
        return []
    idx = index if index is not None else get_occupation_index(model, lang, **index_kwargs)
    if idx is None:
        return []

    import numpy as np

    vector = _encode(model, [query])[0]
    sims = idx.matrix @ vector
    order = np.argsort(-sims)
    out: list[tuple[dict[str, Any], float]] = []
    taken: set[int] = set()
    for row in order:
        occupation_id = int(idx.row_to_occupation[row])
        if occupation_id in taken:
            continue
        taken.add(occupation_id)
        out.append((idx.occupations[occupation_id], float(sims[row])))
        if len(out) >= top_k:
            break
    return out


def confidence_for(top_cosine: float, domain_margin: float) -> str:
    if domain_margin >= CONFIDENCE_HIGH_MARGIN and top_cosine >= CONFIDENCE_HIGH_COSINE:
        return "high"
    if domain_margin >= CONFIDENCE_MEDIUM_MARGIN or top_cosine >= CONFIDENCE_MEDIUM_COSINE:
        return "medium"
    return "low"


def infer_occupation_domain(
    model: Any,
    text: str,
    lang: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    min_cosine: float = MIN_COSINE_FLOOR,
    index: OccupationIndex | None = None,
    **index_kwargs: Any,
) -> dict[str, Any] | None:
    """
    Domain of the retrieved occupation, or None when retrieval is unavailable or too weak to
    beat the keyword fallback.

    Confidence comes from the margin between the best and the runner-up domain, not from the
    absolute cosine: a high cosine with a thin margin is ambiguity, not certainty. When every
    top-k occupation maps to one domain there is no runner-up, and that unanimity scores as the
    widest possible margin.
    """
    hits = retrieve_occupations(model, text, lang, top_k=top_k, index=index, **index_kwargs)
    if not hits:
        return None
    top_occupation, top_cosine = hits[0]
    if top_cosine < min_cosine:
        return None

    per_domain: dict[str, float] = {}
    for occupation, cosine in hits:
        domain = str(occupation.get("domain") or "general")
        if cosine > per_domain.get(domain, -1.0):
            per_domain[domain] = cosine
    ranked = sorted(per_domain.items(), key=lambda kv: -kv[1])
    best_domain, best_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    domain_margin = float(best_score - runner_up)
    occupation_gap = float(top_cosine - hits[1][1]) if len(hits) > 1 else float(top_cosine)

    code = lang_key(lang)

    def _label_of(occupation: dict[str, Any]) -> str:
        labels = occupation.get("labels") if isinstance(occupation.get("labels"), dict) else {}
        return _first_variant(labels.get(code) or labels.get("en") or "")

    evidence = [label[:48] for label in (_label_of(o) for o, _c in hits) if label]

    return {
        "domainCategory": best_domain,
        "confidence": confidence_for(top_cosine, domain_margin),
        "evidenceTokens": evidence[:8],
        "occupation": {
            "uri": top_occupation.get("uri") or "",
            "label": _label_of(top_occupation),
            "isco": top_occupation.get("isco") or "",
            "iscoGroup": top_occupation.get("isco_group") or "",
            "cosine": round(float(top_cosine), 4),
        },
        "domainMargin": round(domain_margin, 4),
        "occupationGap": round(occupation_gap, 4),
    }


def build_occupation_query(resume_data: dict[str, Any], *, max_skills: int = 8) -> str:
    """
    Title-first query: occupation labels are job titles, so titles and skills carry the signal
    while paragraphs of achievements dilute it.
    """
    block = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else {}
    parts: list[str] = []
    target = str(block.get("targetPosition") or "").strip()
    if target:
        parts.append(target)
    for experience in block.get("experiences") or []:
        if isinstance(experience, dict):
            position = str(experience.get("position") or "").strip()
            if position:
                parts.append(position)
    skills: list[str] = []
    for skill in block.get("skills") or []:
        if isinstance(skill, dict) and skill.get("name"):
            skills.append(str(skill["name"]).strip())
        if len(skills) >= max_skills:
            break
    if skills:
        parts.append(", ".join(skills))
    for education in block.get("educations") or []:
        if isinstance(education, dict):
            course = str(education.get("course") or "").strip()
            if course:
                parts.append(course)
    return "\n".join(parts)[:MAX_QUERY_CHARS]


def clear_esco_cache() -> None:
    with _lock:
        _index_cache.clear()
        _occupations_cache.clear()
