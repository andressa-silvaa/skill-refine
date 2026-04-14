"""
Fuse structured seniority (signals/rule) with text-based seniority (neural or lexical).
"""
from __future__ import annotations

LABEL_RANK = {"intern": 0, "junior": 1, "mid": 2, "senior": 3}


def _conf_to_float(conf: str) -> float:
    c = (conf or "low").strip().lower()
    if c == "high":
        return 0.9
    if c == "medium":
        return 0.55
    return 0.25


def _rank(label: str | None) -> int:
    if not label:
        return 1
    return LABEL_RANK.get(str(label).strip().lower(), 1)


def _label_from_rank(r: float) -> str:
    r = max(0.0, min(3.0, r))
    if r < 0.5:
        return "intern"
    if r < 1.5:
        return "junior"
    # Below 2.35: mid; otherwise senior — blends like 0.4*mid+0.6*senior land in senior.
    if r < 2.35:
        return "mid"
    return "senior"


def structural_signals_strength(
    *,
    total_months_experience: int,
    experiences_count: int,
) -> float:
    """0..1 — higher when dates / tenure are informative."""
    m = min(1.0, max(0.0, float(total_months_experience) / 72.0))
    e = min(1.0, max(0.0, float(experiences_count) / 3.0))
    return 0.55 * m + 0.45 * e


def minimal_senior_evidence(
    *,
    total_months: int,
    has_leadership_terms: bool,
    text_hits_senior_pattern: bool,
) -> bool:
    return total_months >= 48 or has_leadership_terms or text_hits_senior_pattern


def fuse_seniority(
    signals_label: str,
    signals_conf: str,
    text_label: str | None,
    text_conf: str,
    signals_strength: float,
    *,
    has_leadership_terms: bool,
    total_months_experience: int,
    text_suggests_senior: bool,
) -> tuple[str, str, dict]:
    """
    Returns (final_label, confidence, meta) where meta is safe for evidence JSON (no raw resume).
    """
    sig_lab = str(signals_label or "junior").strip().lower()
    if sig_lab not in LABEL_RANK:
        sig_lab = "junior"

    if not text_label:
        proposed = sig_lab
        both_low = _conf_to_float(signals_conf) < 0.4
        if proposed == "senior" and both_low:
            if not minimal_senior_evidence(
                total_months=total_months_experience,
                has_leadership_terms=has_leadership_terms,
                text_hits_senior_pattern=text_suggests_senior,
            ):
                proposed = "mid"
        meta = {
            "fusion": "signals_only",
            "weights": {"signals": 1.0, "text": 0.0},
            "signalsStrength": round(signals_strength, 3),
            "textLabel": None,
            "textConfidence": text_conf,
            "signalsLabel": sig_lab,
        }
        return proposed, signals_conf, meta

    w_sig = 0.4 + 0.45 * max(0.0, min(1.0, signals_strength))
    w_txt = 1.0 - w_sig
    tc = _conf_to_float(text_conf)
    if signals_strength < 0.18 and tc >= 0.55:
        w_txt = max(w_txt, 0.58)
        w_sig = 1.0 - w_txt
    if signals_strength < 0.12 and tc >= 0.9:
        w_txt = max(w_txt, 0.72)
        w_sig = 1.0 - w_txt

    r_sig = float(_rank(sig_lab))
    r_txt = float(_rank(text_label))
    blended_rank = w_sig * r_sig + w_txt * r_txt
    proposed = _label_from_rank(blended_rank)

    sc = _conf_to_float(signals_conf)
    both_low = sc < 0.4 and tc < 0.4
    if proposed == "senior":
        ok = minimal_senior_evidence(
            total_months=total_months_experience,
            has_leadership_terms=has_leadership_terms,
            text_hits_senior_pattern=text_suggests_senior,
        )
        if both_low and not ok:
            proposed = "mid"

    if tc > sc:
        conf_out = text_conf
    elif abs(tc - sc) < 0.12:
        conf_out = "medium"
    else:
        conf_out = signals_conf

    meta = {
        "fusion": "signals_ml_text",
        "weights": {"signals": round(w_sig, 3), "text": round(w_txt, 3)},
        "signalsStrength": round(signals_strength, 3),
        "textLabel": text_label,
        "textConfidence": text_conf,
        "signalsLabel": sig_lab,
    }
    return proposed, conf_out, meta
