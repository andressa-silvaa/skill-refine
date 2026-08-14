"""
The ESCO label matrix: loading the taxonomy, embedding it, and caching it per language.

Labels are embedded once per process and persisted under ml/data/reference/esco_embeddings, so a
cold process pays one file read instead of ~1.7k encodings per language. The index is per language
because the labels themselves are per language — which is why reading a resume in the wrong language
costs 29.5 points of occupation retrieval (ml/reports/language_mismatch_v3.md).

Split out of ``esco_retrieval.py`` so that file holds the decision — retrieval, confidence and
domain — without the cache plumbing in the way.
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


def clear_esco_cache() -> None:
    with _lock:
        _index_cache.clear()
        _occupations_cache.clear()
