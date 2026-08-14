"""
Os padrões léxicos que ``resume_signals.py`` usa: cargos, formação, estágio, e anos por extenso.

Tabela, não decisão. Duas dessas listas — ``_TECH_EDU_RE`` e ``_NON_TECH_EDU_RE`` — decidem se a
formação "combina" com o alvo, e substituí-las por similaridade no encoder foi tentado e medido como
não separável (ml/reports/education_alignment_v3.md). Ler o relatório antes de tentar de novo.
"""
from __future__ import annotations

import re


_TECH_ROLE_RE = re.compile(
    r"programador|programadora|developer|desenvolvedor|desenvolvedora|software|"
    r"\bdevops\b|backend|front\s*[-]?end|full\s*[-]?stack|dados|data\s*science|"
    r"cientista\s+de\s+dados|engenheir[oa]?\s+de\s+software|engenheir[oa]?\s+de\s+dados|"
    r"analista\s+de\s+sistemas|analista\s+de\s+dados|sistemas\s+de\s+informa|"
    r"ti\b|i\.t\.|tecnolog|computa\w*|dev\s|"
    r"web\s+developer|mobile|android|ios|cloud|cyber|seguran\w*\s+da\s+informa",
    re.I,
)

# Formação claramente de TI / STEM útil para dev
_TECH_EDU_RE = re.compile(
    r"computa\w*|inform[aá]tica|software|sistemas\s+de\s+informa|ci[eê]ncia[s]?\s+da\s+computa|"
    r"engenharia\s+de\s+software|engenharia\s+da\s+computa|engenharia\s+el[eé]trica|"
    r"engenharia\s+mecatr|an[aá]lise\s+e\s+desenvolvimento|ads\b|t[eé]cnico\s+em\s+inform[aá]tica|"
    r"computer\s+science|software\s+engineering|data\s+science|machine\s+learning|"
    r"matem[aá]tica|estat[ií]stica|f[ií]sica|ciberseguran|redes\s+de\s+comput",
    re.I,
)

# Cursos tipicamente fora de TI (quando o alvo é tech)
_NON_TECH_EDU_RE = re.compile(
    r"biologia|biological|biomedic|medicina|enfermagem|direito|letras|"
    r"hist[oó]ria|geografia|pedagogia|psicologia|nutri\w*|jornalismo|"
    r"marketing|contabil|administra|arquitetura\s+e\s+urbanismo|"
    r"veterin[aá]ria|odontologia|farm[aá]cia",
    re.I,
)

# Limites de palavra: evita "intern" em "interno", "internal", "desenvolvimento" (falso estágio).
_INTERN_TITLE_RE = re.compile(
    r"\best[aá]gio\b|\bestagi[aá]ri[oa]?\b|\binternship\b|\bintern\b|\btrainee\b",
    re.I,
)

_STUDENT_RE = re.compile(
    r"\bestudante\b|\bstudent\b|\balun[oa]\b",
    re.I,
)

# Anos explícitos só em campos de carreira (evita "curso de 2 anos" em formação).
# Aceita "2+ anos", "5 + anos" (comum em resumos tipo LinkedIn).
_WORK_YEARS_PATTERN = re.compile(r"(\d+)\s*\+\s*(?:anos?|years?|años?)|(\d+)\s+(?:anos?|years?|años?)", re.I)
_PT_WORD_TO_INT = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "três": 3,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
}
_PT_WORD_YEARS_PATTERN = re.compile(
    r"\b(um|uma|dois|duas|tr[eê]s|tres|quatro|cinco|seis|sete|oito|nove|dez)\s+anos?\b",
    re.I,
)

_JUNIOR_TITLE_HINT = re.compile(r"j[úu]nior|junior|\bjr\.?\b", re.I)

_TECH_SKILL_RE = re.compile(
    r"\b(python|java|javascript|typescript|react|node|sql|django|flask|fastapi|"
    r"angular|vue|kotlin|swift|go\b|rust|c\+\+|\.net|aws|azure|docker|kubernetes|git)\b",
    re.I,
)
