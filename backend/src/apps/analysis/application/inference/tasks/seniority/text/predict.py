"""
Text seniority: HF classifier if bundle present, else lexical evidence (pt/en/es) for fusion tests.
"""
from __future__ import annotations

import logging
import re
from contextlib import nullcontext
from typing import Any

logger = logging.getLogger(__name__)

ORDER = ("intern", "junior", "mid", "senior")

_SENIOR_PATTERNS = re.compile(
    r"\b(s[êe]nior|sr\.?|staff|principal|distinguished|"
    r"tech\s*lead|engineering\s*lead|l[ií]der\s+(de\s+)?tecnolog|l[ií]der\s+t[ée]cnic|"
    r"head\s+of\s+engineering|cto|vp\s+engineering|arquitet[oa]\s+de\s+software|"
    r"10\s*(?:anos?|years?|años)|"
    r"\b(?:8|9|1[0-5])\s*(?:anos?|years?|años)\s+(?:de\s+)?(?:experiência|experience|experiencia))\b",
    re.I,
)
_INTERN_PATTERNS = re.compile(
    r"\b(estagi[áa]ri[oa]?|intern(?:ship)?|trainee|primeiro\s+emprego|first\s+job)\b",
    re.I,
)
_SUPERVISION_VERBS = re.compile(
    r"\b(mentorei|liderei|treinei|orientei|supervisionei|coordenei|gerenciei|ensinei|"
    r"mentored|led|trained|supervised|coordinated|managed|taught)\b",
    re.I,
)
_JUNIOR_PATTERNS = re.compile(
    r"\b(j[uú]nior|jr\.?|entry[\s-]?level)\b",
    re.I,
)
_MID_PATTERNS = re.compile(
    r"\b(pleno|mid[\s-]?level|desenvolvedor\s+pleno|software\s+engineer\s+ii|"
    r"\b3\s*(?:anos?|years?)\b)\b",
    re.I,
)


def _normalize_label(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip().lower()
    mapping = {
        "label_0": None,
        "label_1": None,
        "stagiaire": "intern",
        "trainee": "intern",
        "estagiario": "intern",
        "estagiário": "intern",
        "estagiaria": "intern",
        "estagiária": "intern",
        "intern": "intern",
        "internship": "intern",
        "becario": "intern",
        "becaria": "intern",
        "pasante": "intern",
        "practicas": "intern",
        "prácticas": "intern",
        "jr": "junior",
        "jr.": "junior",
        "junior": "junior",
        "júnior": "junior",
        "entry-level": "junior",
        "entry level": "junior",
        "pleno": "mid",
        "mid": "mid",
        "mid-level": "mid",
        "middle": "mid",
        "semi-senior": "mid",
        "semisenior": "mid",
        "sr": "senior",
        "sr.": "senior",
        "senior": "senior",
        "sênior": "senior",
        "staff": "senior",
        "principal": "senior",
    }
    if s in mapping and mapping[s]:
        return mapping[s]
    if s in ORDER:
        return s
    return None


def _max_prob_confidence(max_p: float) -> str:
    if max_p >= 0.55:
        return "high"
    if max_p >= 0.38:
        return "medium"
    return "low"


def _lexical_seniority(text: str) -> tuple[str | None, str, float]:
    """Heuristic label from sanitized text (no PII). For fallback / TCC regression when bundle missing."""
    t = (text or "").lower()
    if not t.strip():
        return None, "low", 0.0
    score = 0.0
    if _SENIOR_PATTERNS.search(t):
        score += 3.0
    if _INTERN_PATTERNS.search(t) and not _SUPERVISION_VERBS.search(t):
        score -= 3.0
    elif _JUNIOR_PATTERNS.search(t):
        score -= 2.0
    if _MID_PATTERNS.search(t) and score < 2.5:
        score += 0.5
    if "líder" in t or "lider" in t or "lead" in t:
        score += 1.0
    if score >= 2.5:
        return "senior", "high" if score >= 3.5 else "medium", min(1.0, score / 4.0)
    if score <= -2.5:
        return "intern", "medium", 0.5
    if score <= -1.0:
        return "junior", "medium", 0.45
    if 0.5 <= score < 2.5:
        return "mid", "low", 0.35
    return None, "low", 0.0


def _predict_probe(
    probe_bundle: dict[str, Any],
    encoder: Any,
    text: str,
    resume_data: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Linear probe over the frozen multilingual encoder already loaded for target_fit.

    Trained on ``band_target`` from text alone. Human review of 46 resumes put that label at ~94.9%
    against ~78.5% for the LLM teacher, so it is the primary label for a text-only model — but only for
    a text-only model: anything reading month counts would be relearning the generator's formula.
    """
    from apps.analysis.application.inference.text_probe import encode_for_bundle

    head = (probe_bundle.get("heads") or {}).get("band")
    if head is None:
        return None
    matrix = encode_for_bundle(probe_bundle, encoder, text, resume_data)
    probabilities = [float(p) for p in head.predict_proba(matrix)[0]]
    classes = [str(c) for c in head.classes_]
    if not probabilities:
        return None
    probs_map: dict[str, float] = {}
    for raw_label, probability in zip(classes, probabilities):
        key = _normalize_label(raw_label) or raw_label
        probs_map[key] = probability
    best = max(range(len(probabilities)), key=lambda i: probabilities[i])
    label = _normalize_label(classes[best])
    if label is None:
        return None
    return {
        "label": label,
        "confidence": _max_prob_confidence(max(probabilities)),
        "probs": probs_map,
        "source": "probe",
    }


def predict_text_seniority(
    sanitized_text: str,
    language: str,
    bundle: dict[str, Any] | None,
    *,
    allow_lexical_fallback: bool = True,
    probe_bundle: dict[str, Any] | None = None,
    embeddings_model: Any = None,
    resume_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Returns dict: label (or None), confidence (low/medium/high), probs, source.

    Source is one of probe|neural|lexical|none, in cascade order. The probe leads because it is the
    only step fitted on this corpus; the HF bundle and the lexical rules stay behind it as fallbacks.
    """
    text = (sanitized_text or "").strip()
    if not text and not allow_lexical_fallback:
        return {"label": None, "confidence": "low", "probs": {}, "source": "none"}

    if text and probe_bundle and embeddings_model is not None and resume_data is not None:
        try:
            predicted = _predict_probe(probe_bundle, embeddings_model, text, resume_data)
            if predicted:
                return predicted
        except Exception as exc:
            logger.warning("text_seniority probe predict failed: %s", exc)

    if bundle and bundle.get("model") is not None and bundle.get("tokenizer") is not None:
        try:
            import torch
        except Exception:
            torch = None
        try:
            model = bundle["model"]
            tokenizer = bundle["tokenizer"]
            inputs = tokenizer(
                text[:2000],
                return_tensors="pt",
                truncation=True,
                max_length=256,
                padding=True,
            )
            ctx = getattr(torch, "inference_mode", None) if torch else None
            context = ctx() if callable(ctx) else (torch.no_grad() if torch else nullcontext())
            with context:
                out = model(**inputs)
                logits = out.logits
                if torch is not None:
                    probs_t = torch.softmax(logits, dim=-1).squeeze(0)
                    probs_list = [float(x) for x in probs_t.tolist()]
                else:
                    probs_list = []
            id2label = getattr(getattr(model, "config", None), "id2label", None) or {}
            if not probs_list and len(logits.shape) == 2:
                import math

                row = logits.squeeze(0).tolist()
                m = max(row)
                exps = [math.exp(x - m) for x in row]
                s = sum(exps) or 1.0
                probs_list = [e / s for e in exps]
            best_i = max(range(len(probs_list)), key=lambda i: probs_list[i])
            raw_lab = id2label.get(best_i) if isinstance(id2label, dict) else None
            if raw_lab is None and isinstance(id2label, dict):
                raw_lab = id2label.get(str(best_i))
            label = _normalize_label(str(raw_lab)) if raw_lab is not None else None
            if label is None and 0 <= best_i < len(ORDER):
                label = ORDER[best_i] if len(probs_list) == len(ORDER) else None
            probs_map = {}
            for i, p in enumerate(probs_list):
                lab = id2label.get(i) if isinstance(id2label, dict) else str(i)
                nk = _normalize_label(str(lab)) if lab is not None else None
                key = nk or (ORDER[i] if i < len(ORDER) else str(i))
                probs_map[key] = float(p)
            max_p = max(probs_list) if probs_list else 0.0
            conf = _max_prob_confidence(max_p)
            if label:
                return {"label": label, "confidence": conf, "probs": probs_map, "source": "neural"}
        except Exception as exc:
            logger.warning("text_seniority neural predict failed: %s", exc)

    if allow_lexical_fallback:
        lab, conf, _st = _lexical_seniority(text)
        if lab:
            return {
                "label": lab,
                "confidence": conf,
                "probs": {lab: 0.55},
                "source": "lexical",
            }

    return {"label": None, "confidence": "low", "probs": {}, "source": "none"}
