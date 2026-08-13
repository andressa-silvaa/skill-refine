"""
Frozen-encoder text probes: the feature transform, and the loader that refuses a mismatched bundle.

A probe is a linear model over sentence-embeddings of the sanitized resume. The encoder is the
multilingual MiniLM already resident for target_fit, so a probe costs one matmul per analysis and no
extra memory.

The encoder caps input at 128 word-pieces and a resume runs to ~600 words, so a single ``encode``
call would silently read the summary and throw the experience away. The transform therefore splits
the document into fixed word windows, encodes every window, and averages them into one vector.

One average over the whole resume is not enough, though: a 40-word skills list and two lines of
achievement prose land in the same mean, and the long block wins. So the transform embeds each of the
four evidence blocks separately and concatenates them, which keeps them addressable by the head. That
was measured, not assumed — it is worth +8 accuracy points on seniority and +14 on quality against
the single-mean version (ml/reports/text_probes_v3.md).

Note what the block split also buys: ``summary``, ``roles``, ``bullets`` and ``credentials`` carry no
month counts at all. A head fitted on them alone cannot be re-learning the generator's tenure
formula, which is the circularity that killed the v2 seniority model.

That transform is identified by ``TRANSFORM_ID`` and written into the bundle metadata. Training and
inference call the same function here, and ``load_probe_bundle`` refuses a bundle whose metadata
names a different transform or a different embedding width — the same interlock that
``loader_signals_model`` grew after a silent train/serve skew.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)

TRANSFORM_ID = "sections_chunked_mean_60w_l2_v2"
BULLET_TRANSFORM_ID = "bullet_mean_l2_v1"
CHUNK_WORDS = 60
MAX_CHUNKS = 12
SECTION_ORDER = ("summary", "roles", "bullets", "credentials")


def chunk_text(text: str, *, chunk_words: int = CHUNK_WORDS, max_chunks: int = MAX_CHUNKS) -> list[str]:
    """Fixed word windows, so no part of the resume is dropped by the encoder's 128-token cap."""
    words = str(text or "").split()
    if not words:
        return []
    chunks = [
        " ".join(words[start : start + chunk_words])
        for start in range(0, len(words), chunk_words)
    ]
    return chunks[:max_chunks]


def embed_documents(encoder: Any, texts: Sequence[str], *, batch_size: int = 64) -> Any:
    """
    Mean of the window embeddings per document, L2-normalized. Returns (n_docs, dim).

    Every window of every document goes into one ``encode`` call, which is what makes embedding the
    whole corpus a minute rather than an hour.
    """
    import numpy as np

    flat: list[str] = []
    spans: list[tuple[int, int]] = []
    for text in texts:
        chunks = chunk_text(text)
        start = len(flat)
        flat.extend(chunks)
        spans.append((start, len(flat)))

    if not flat:
        return np.zeros((len(texts), 0), dtype=np.float32)

    encoded = np.asarray(
        encoder.encode(flat, batch_size=batch_size, show_progress_bar=False),
        dtype=np.float32,
    )
    dim = encoded.shape[1]
    out = np.zeros((len(texts), dim), dtype=np.float32)
    for row, (start, end) in enumerate(spans):
        if end > start:
            out[row] = encoded[start:end].mean(axis=0)
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return out / norms


def embed_one(encoder: Any, text: str) -> Any:
    """Single-document convenience wrapper; returns a (1, dim) matrix ready for ``predict_proba``."""
    return embed_documents(encoder, [text])


def build_bullet_matrix(encoder: Any, bullets: Sequence[str]) -> Any:
    """
    One L2-normalized embedding per bullet. Returns (n_bullets, dim).

    A bullet needs no section split and no windowing: measured over the labelled corpus they run
    15.8 words on average and 44 at the longest, so not one reaches the 60-word window that
    ``chunk_text`` exists to handle. The mean below is therefore over a single chunk, which makes
    this an exact encoding rather than an approximation of one.

    Kept as a named transform anyway, because the bundle metadata records it and
    ``load_probe_bundle`` refuses a head whose transform does not match what inference computes.
    """
    return embed_documents(encoder, list(bullets))


def section_texts(resume_data: dict[str, Any]) -> dict[str, str]:
    """
    Locate the four evidence blocks. Field lookup and truncation only — no judgement here.

    Kept byte-identical to the training-side splitter, because a probe fed differently-assembled
    blocks than it was fitted on is the same train/serve skew that ``feature_transform`` exists to
    catch, except silent.
    """
    data = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else resume_data
    data = data if isinstance(data, dict) else {}

    roles: list[str] = []
    bullets: list[str] = []
    target = str(data.get("targetPosition") or "").strip()
    if target:
        roles.append(target)
    experiences = data.get("experiences") or []
    if isinstance(experiences, list):
        for exp in experiences[:12]:
            if not isinstance(exp, dict):
                continue
            title = str(exp.get("position") or exp.get("title") or "").strip()
            if title:
                roles.append(f"{title} (atual)" if exp.get("isCurrent") else title)
            for bullet in (exp.get("description") or [])[:10]:
                text = str(bullet).strip()
                if text:
                    bullets.append(text)

    credentials: list[str] = []
    for education in (data.get("educations") or data.get("education") or [])[:6]:
        if isinstance(education, dict):
            course = str(education.get("course") or education.get("degree") or "").strip()
            if course:
                credentials.append(course)
    for skill in (data.get("skills") or [])[:80]:
        name = str(skill.get("name") or "").strip() if isinstance(skill, dict) else str(skill).strip()
        if name:
            credentials.append(name)

    return {
        "summary": _squeeze(str(data.get("summary") or "")),
        "roles": _squeeze(" \n".join(roles)),
        "bullets": _squeeze(" \n".join(bullets)),
        "credentials": _squeeze(", ".join(credentials)),
    }


def _squeeze(text: str) -> str:
    import re

    return re.sub(r"\s+", " ", (text or "").strip())


def build_feature_matrix(
    encoder: Any,
    resume_payloads: Sequence[dict[str, Any]],
    document_texts: Sequence[str],
    *,
    include_document: bool,
) -> Any:
    """
    Assemble probe inputs: the four section vectors per resume, optionally plus the document vector.

    ``include_document`` comes from bundle metadata rather than a constant, because the two variants
    differ in width and in what they may see — the section blocks carry no month counts, the document
    block does.

    Training calls this with the whole corpus and inference with one row, so there is exactly one
    implementation of the feature layout and no opportunity for the two to drift.
    """
    import numpy as np

    sections = [section_texts(payload) for payload in resume_payloads]
    blocks = [
        embed_documents(encoder, [item.get(name, "") for item in sections])
        for name in SECTION_ORDER
    ]
    if include_document:
        blocks.append(embed_documents(encoder, list(document_texts)))
    matrix = np.concatenate(blocks, axis=1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def build_feature_row(
    encoder: Any,
    resume_data: dict[str, Any],
    document_text: str,
    *,
    include_document: bool,
) -> Any:
    return build_feature_matrix(
        encoder, [resume_data], [document_text], include_document=include_document
    )


def load_probe_bundle(
    model_dir: Path, *, expected_task: str, expected_transform: str = TRANSFORM_ID
) -> dict[str, Any]:
    """
    Load ``model.joblib`` + ``metadata.json`` and assert the bundle matches this code.

    Raises on any mismatch rather than degrading quietly: a probe fed features it was not trained on
    returns confident nonsense, which is exactly the failure that made the old seniority model answer
    ``intern`` for every real resume.
    """
    meta_path = model_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"missing metadata.json in {model_dir}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    task = str(meta.get("task") or "")
    if task != expected_task:
        raise ValueError(f"metadata task {task!r} incompatible, expected {expected_task!r}")
    transform = str(meta.get("feature_transform") or "")
    if transform != expected_transform:
        raise ValueError(
            f"feature_transform {transform!r} != inference transform {expected_transform!r}"
        )

    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError("joblib required to load a text probe bundle") from exc

    model_path = model_dir / "model.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"missing model.joblib in {model_dir}")
    bundle = joblib.load(model_path)
    if not isinstance(bundle, dict) or "heads" not in bundle:
        raise ValueError("invalid probe bundle: missing heads")
    bundle["_metadata"] = meta
    bundle["_model_dir"] = str(model_dir)
    return bundle


def bundle_dim(bundle: dict[str, Any]) -> int:
    meta = bundle.get("_metadata") if isinstance(bundle.get("_metadata"), dict) else {}
    try:
        return int(meta.get("embedding_dim") or 0)
    except (TypeError, ValueError):
        return 0


def encode_for_bundle(
    bundle: dict[str, Any],
    encoder: Any,
    text: str,
    resume_data: dict[str, Any] | None = None,
) -> Any:
    """Build the feature row this bundle expects and check its width before any head sees it."""
    meta = bundle.get("_metadata") if isinstance(bundle.get("_metadata"), dict) else {}
    include_document = bool(meta.get("include_document", True))
    if resume_data is None:
        raise ValueError("resume_data required: this transform reads the resume section by section")
    matrix = build_feature_row(encoder, resume_data, text, include_document=include_document)
    expected = bundle_dim(bundle)
    got = int(matrix.shape[1]) if getattr(matrix, "ndim", 0) == 2 else 0
    if expected and got != expected:
        raise ValueError(f"feature width {got} != bundle width {expected}")
    if not got:
        raise ValueError("empty features: nothing to score")
    return matrix


def probe_metadata_for_task(bundle: dict[str, Any] | None, *, provider: str) -> dict[str, Any]:
    if not bundle:
        return {}
    meta = bundle.get("_metadata") if isinstance(bundle.get("_metadata"), dict) else {}
    return {
        "provider": provider,
        "metadata": {
            "model_name_base": str(meta.get("model_name") or provider),
            "model_version": str(meta.get("model_version") or ""),
            "dataset_version": str(meta.get("dataset_version") or ""),
            "feature_transform": TRANSFORM_ID,
        },
    }
