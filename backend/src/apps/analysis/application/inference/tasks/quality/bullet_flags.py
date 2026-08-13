"""
Per-bullet attribute flags from the ``bullet_probe`` head, replacing three regex families.

``METRICS_PATTERN``, ``ACTION_VERBS`` and ``LEADERSHIP_WORDS`` each decide a per-bullet fact by
scanning a whole-document string. Measured against a two-annotator consensus they recover 0.77 /
0.21 / 0.32 of the positives they exist to find, and ``LEADERSHIP_WORDS`` scores below the majority
class — answering "no leadership" to everything beats it. The probe reads one bullet at a time and
more than doubles F1 on two of the three (ml/reports/bullet_probe_v3.md).

Two behaviour changes are deliberate and worth naming, because they are not strictly upgrades:

* **Evidence is narrowed to bullets.** The regexes scanned summary, titles and skills too, which is
  how ``LEADERSHIP_WORDS`` fired on "supervisar la tensión y la corriente" and on a job title alone.
  The probe reads only the described work. A manager whose bullets describe no direction of people
  now reads as no-leadership, which is the intended reading of the attribute.
* **The flags stay document-level booleans.** Callers (``derive_insights``, ``fuse_seniority``) take
  a single bool, so per-bullet answers are aggregated with "any bullet". The per-bullet detail is
  returned alongside so a future ranking consumer can use it without another pass.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

ATTRIBUTES = ("quantified", "outcome", "leadership")
FLAG_FOR_ATTRIBUTE = {
    "quantified": "has_metrics",
    "outcome": "has_action_verbs",
    "leadership": "has_leadership",
}
MAX_BULLETS = 60


def extract_bullets(resume_data: dict[str, Any] | None) -> list[str]:
    if not isinstance(resume_data, dict):
        return []
    data = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else resume_data
    bullets: list[str] = []
    for experience in data.get("experiences") or []:
        if not isinstance(experience, dict):
            continue
        for raw in experience.get("description") or []:
            text = str(raw or "").strip()
            if text:
                bullets.append(text)
            if len(bullets) >= MAX_BULLETS:
                return bullets
    return bullets


def predict_bullet_flags(
    bundle: dict[str, Any] | None,
    encoder: Any,
    resume_data: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """
    Score every bullet on the three attributes. Returns ``None`` when the probe cannot answer, so the
    caller keeps the regex rather than publishing a silently empty result.

    A resume with no bullets is a real answer, not a failure: every attribute is false because there
    is no described work to carry it. That is returned with ``bullet_count`` 0 rather than ``None``.
    """
    if not bundle or encoder is None:
        return None
    heads = bundle.get("heads") if isinstance(bundle, dict) else None
    if not isinstance(heads, dict) or not all(a in heads for a in ATTRIBUTES):
        return None

    bullets = extract_bullets(resume_data)
    if not bullets:
        return {
            "flags": {flag: False for flag in FLAG_FOR_ATTRIBUTE.values()},
            "bullets": [],
            "bullet_count": 0,
            "counts": {attribute: 0 for attribute in ATTRIBUTES},
        }

    try:
        from apps.analysis.application.inference.text_probe import build_bullet_matrix

        matrix = build_bullet_matrix(encoder, bullets)
        predictions: dict[str, list[bool]] = {}
        for attribute in ATTRIBUTES:
            predictions[attribute] = [bool(v) for v in heads[attribute].predict(matrix)]
    except Exception as exc:
        logger.warning("bullet_probe failed to score %d bullets: %s", len(bullets), exc)
        return None

    per_bullet = [
        {
            "index": i,
            **{attribute: predictions[attribute][i] for attribute in ATTRIBUTES},
        }
        for i in range(len(bullets))
    ]
    counts = {attribute: sum(predictions[attribute]) for attribute in ATTRIBUTES}
    flags = {
        FLAG_FOR_ATTRIBUTE[attribute]: counts[attribute] > 0 for attribute in ATTRIBUTES
    }
    return {
        "flags": flags,
        "bullets": per_bullet,
        "bullet_count": len(bullets),
        "counts": counts,
    }
