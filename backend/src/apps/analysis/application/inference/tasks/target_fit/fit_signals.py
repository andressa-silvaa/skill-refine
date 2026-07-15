"""
Structural, explainable signals for target role fit (any profession).
No LLM: token overlap between target/job text and resume fields.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

from .domain_inference import infer_domain_category

_STOPWORDS_PT: frozenset[str] = frozenset(
    """
    de da do das dos em no na nos nas um uma uns unas por para com sem sobre entre
    que o a os as pelo pela pelos pelas ao à aos às seu sua seus suas este esta esse essa
    como mais menos muito pouco já ainda também apenas todo todos toda todas
    """.split()
)
_STOPWORDS_EN: frozenset[str] = frozenset(
    """
    the a an and or for to of in on at by from with without into over per as is are was
    be been being this that these those your our their any all each both more most some
    """.split()
)
_STOPWORDS_ES: frozenset[str] = frozenset(
    """
    el la los las un una unos unas de del al y o en con sin por para sobre entre que como
    más menos muy poco ya también solo todo todos toda todas su sus este esta estos estas
    """.split()
)

# Extra terms when only targetPosition is available (broad, non-IT-specific)
_DOMAIN_HINT_TERMS: dict[str, tuple[str, ...]] = {
    "health": ("clínica", "hospital", "paciente", "enfermagem", "saúde", "clinical", "patient", "care"),
    "education": ("ensino", "aula", "pedagogia", "academic", "student", "curriculum", "school"),
    "legal": ("jurídico", "contrato", "legal", "compliance", "court", "litigation"),
    "finance": ("financeiro", "contábil", "orçamento", "investimento", "audit", "banking", "tax"),
    "engineering": ("projeto", "obra", "engenharia", "design", "plant", "technical", "spec"),
    "marketing": ("marca", "campanha", "conteúdo", "growth", "brand", "seo", "crm"),
    "sales": ("vendas", "comercial", "cliente", "negociação", "account", "revenue"),
    "technology": ("software", "sistema", "dados", "aplicação", "platform", "technical"),
    "administrative": ("administrativo", "escritório", "agenda", "processo", "office"),
    "science": ("laboratório", "pesquisa", "ensaio", "publicação", "research", "analysis"),
    "hr": ("recrutamento", "talento", "people", "culture", "payroll", "training"),
    "operations": ("logística", "estoque", "produção", "supply", "process", "quality"),
    "creative": ("design", "criativo", "visual", "brand", "content", "portfolio"),
    "general": ("senior", "junior", "pleno", "líder", "coordenador", "manager", "lead", "chief"),
}


def _fold(s: str) -> str:
    t = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _stopwords_for_lang(lang: str) -> frozenset[str]:
    lc = (lang or "pt-BR").lower()
    if lc.startswith("en"):
        return _STOPWORDS_EN
    if lc.startswith("es"):
        return _STOPWORDS_ES
    return _STOPWORDS_PT


def _extract_terms(raw: str, lang: str, *, max_terms: int = 28) -> list[str]:
    sw = _stopwords_for_lang(lang)
    folded = _fold(raw)
    folded = re.sub(r"[^\w\s\-/+]", " ", folded, flags=re.UNICODE)
    tokens = [t for t in re.split(r"\s+", folded) if len(t) >= 3 and t not in sw]
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= max_terms:
            break
    return out


def _resume_corpus(data: dict[str, Any]) -> str:
    d = data.get("data") if isinstance(data.get("data"), dict) else {}
    parts: list[str] = []
    parts.append(str(d.get("targetPosition") or ""))
    parts.append(str(d.get("summary") or ""))
    for sk in d.get("skills") or []:
        if isinstance(sk, dict):
            parts.append(str(sk.get("name") or ""))
    for ex in d.get("experiences") or []:
        if not isinstance(ex, dict):
            continue
        parts.append(str(ex.get("company") or ""))
        parts.append(str(ex.get("position") or ""))
        for b in ex.get("description") or []:
            parts.append(str(b))
    for ed in d.get("educations") or []:
        if isinstance(ed, dict):
            parts.append(str(ed.get("course") or ""))
            parts.append(str(ed.get("degree") or ""))
            parts.append(str(ed.get("institution") or ""))
    contact = d.get("contact") if isinstance(d.get("contact"), dict) else {}
    for lk in ("linkedin", "github", "portfolio", "website"):
        parts.append(str(contact.get(lk) or ""))
    return " \n ".join(parts)


def _experience_corpus(data: dict[str, Any]) -> str:
    d = data.get("data") if isinstance(data.get("data"), dict) else {}
    parts: list[str] = []
    for ex in d.get("experiences") or []:
        if not isinstance(ex, dict):
            continue
        parts.append(str(ex.get("position") or ""))
        for b in ex.get("description") or []:
            parts.append(str(b))
    return " \n ".join(parts)


def term_matches_folded_corpus(term: str, folded_corpus: str) -> bool:
    """Accent-folded match: exact substring or shared 5-char prefix with corpus words."""
    if len(term) < 3:
        return False
    if term in folded_corpus:
        return True
    if len(term) < 5:
        return False
    prefix = term[:5]
    for tw in re.findall(r"\w{4,}", folded_corpus):
        if tw.startswith(prefix) or term.startswith(tw[:5]):
            return True
    return False


def _education_corpus(data: dict[str, Any]) -> str:
    d = data.get("data") if isinstance(data.get("data"), dict) else {}
    parts: list[str] = []
    for ed in d.get("educations") or []:
        if isinstance(ed, dict):
            parts.append(str(ed.get("course") or ""))
            parts.append(str(ed.get("degree") or ""))
            parts.append(str(ed.get("institution") or ""))
    return " \n ".join(parts)


def _skill_names(data: dict[str, Any]) -> list[str]:
    d = data.get("data") if isinstance(data.get("data"), dict) else {}
    out: list[str] = []
    for sk in d.get("skills") or []:
        if isinstance(sk, dict) and sk.get("name"):
            out.append(str(sk["name"]))
    return out


def _portfolio_evidence(data: dict[str, Any]) -> bool:
    d = data.get("data") if isinstance(data.get("data"), dict) else {}
    c = d.get("contact") if isinstance(d.get("contact"), dict) else {}
    for k in ("portfolio", "github", "website"):
        v = (c.get(k) or "").strip()
        if len(v) > 6 and "http" in v.lower():
            return True
    return False


@dataclass
class TargetFitSignals:
    required_terms_total: int = 0
    required_terms_hit: int = 0
    required_terms_matched: list[str] = field(default_factory=list)
    required_terms_missing: list[str] = field(default_factory=list)
    skills_total: int = 0
    skills_hit: int = 0
    skills_matched: list[str] = field(default_factory=list)
    experience_keyword_hits: int = 0
    education_alignment: str = "weak"
    portfolio_evidence: bool = False
    completeness_score: int = 0

    def to_public_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def extract_target_fit_signals(
    resume_data: dict[str, Any],
    target_position: str,
    job_text: str | None,
    lang: str,
    *,
    completeness_score: int = 0,
) -> TargetFitSignals:
    target_position = (target_position or "").strip()
    job = (job_text or "").strip()
    target_dom = infer_domain_category(f"{target_position} {job}".strip(), lang=lang)
    dom_cat = str(target_dom.get("domainCategory") or "general")

    terms = _extract_terms(f"{target_position}\n{job}", lang)
    if not job and terms:
        hints = _DOMAIN_HINT_TERMS.get(dom_cat) or _DOMAIN_HINT_TERMS["general"]
        for h in hints:
            fh = _fold(h)
            if fh not in {_fold(x) for x in terms}:
                terms.append(fh)
        terms = terms[:28]

    if not terms and target_position:
        terms = _extract_terms(target_position, lang, max_terms=12)

    corpus = _fold(_resume_corpus(resume_data))
    exp_corpus = _fold(_experience_corpus(resume_data))
    edu_corpus = _fold(_education_corpus(resume_data))
    skill_list = [_fold(s) for s in _skill_names(resume_data)]

    matched: list[str] = []
    missing: list[str] = []
    hits_exp = 0
    for term in terms:
        if term_matches_folded_corpus(term, corpus):
            matched.append(term[:64])
            if term_matches_folded_corpus(term, exp_corpus):
                hits_exp += 1
        else:
            missing.append(term[:64])

    sk_hit = 0
    sk_matched: list[str] = []
    for term in terms:
        for sk in skill_list:
            if term in sk or sk in term:
                sk_hit += 1
                if term not in sk_matched:
                    sk_matched.append(term[:64])
                break

    edu_align = "weak"
    for term in terms[:15]:
        if term and term_matches_folded_corpus(term, edu_corpus):
            edu_align = "strong"
            break
    if edu_align == "weak" and dom_cat != "general":
        dom_hints = _DOMAIN_HINT_TERMS.get(dom_cat, ())
        for h in dom_hints:
            if _fold(h) in edu_corpus:
                edu_align = "medium"
                break

    return TargetFitSignals(
        required_terms_total=len(terms),
        required_terms_hit=len(matched),
        required_terms_matched=matched[:12],
        required_terms_missing=missing[:12],
        skills_total=min(len(terms), 12) or len(terms),
        skills_hit=min(sk_hit, len(terms)),
        skills_matched=sk_matched[:12],
        experience_keyword_hits=hits_exp,
        education_alignment=edu_align,
        portfolio_evidence=_portfolio_evidence(resume_data),
        completeness_score=int(completeness_score),
    )
