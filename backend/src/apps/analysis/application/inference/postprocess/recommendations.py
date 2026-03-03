"""
Build recommendations with example templates (no LLM).
Example keys for i18n; params for interpolation.
"""
from __future__ import annotations

from typing import Any

EXAMPLE_TEMPLATES: dict[str, dict[str, str]] = {
    "analysis.insights.improvements.add_metrics": {
        "pt-BR": "Troque 'Responsável por X' por 'Liderei X, reduzindo custos em 20%'.",
        "en-US": "Replace 'Responsible for X' with 'Led X, reducing costs by 20%'.",
        "es-ES": "Reemplace 'Responsable de X' por 'Lideré X, reduciendo costos en 20%'.",
    },
    "analysis.insights.improvements.use_action_verbs": {
        "pt-BR": "Use verbos de ação: desenvolvi, implementei, coordenei, gerenciei.",
        "en-US": "Use action verbs: developed, implemented, coordinated, managed.",
        "es-ES": "Use verbos de acción: desarrollé, implementé, coordiné, gestioné.",
    },
    "analysis.insights.improvements.relevant_links": {
        "pt-BR": "Adicione links para LinkedIn, GitHub ou portfólio.",
        "en-US": "Add links to LinkedIn, GitHub or portfolio.",
        "es-ES": "Agregue enlaces a LinkedIn, GitHub o portafolio.",
    },
    "analysis.insights.improvements.improve_summary": {
        "pt-BR": "Resumo curto. Inclua anos de experiência e área de atuação.",
        "en-US": "Short summary. Include years of experience and focus area.",
        "es-ES": "Resumen corto. Incluya años de experiencia y área de enfoque.",
    },
    "analysis.insights.improvements.ats_keywords": {
        "pt-BR": "Inclua palavras-chave da vaga para passar em ATS.",
        "en-US": "Include job keywords to pass ATS screening.",
        "es-ES": "Incluya palabras clave del trabajo para pasar ATS.",
    },
}


def build_recommendations(
    insights: dict[str, list[dict[str, Any]]],
    language: str = "pt-BR",
) -> list[dict[str, Any]]:
    """
    For each improvement, add example_key/example_params for i18n templates.
    """
    improvements = insights.get("improvements") or []
    lang = (language or "pt-BR").strip()
    result = []
    for imp in improvements:
        key = imp.get("key") or ""
        rec = dict(imp)
        templates = EXAMPLE_TEMPLATES.get(key, {})
        example = templates.get(lang) or templates.get("pt-BR") or templates.get("en-US") or ""
        if example:
            rec["example_key"] = f"{key}.example"
            rec["example_params"] = {"text": example}
        result.append(rec)
    return result
