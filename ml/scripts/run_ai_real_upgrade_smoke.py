#!/usr/bin/env python3
"""
Run a few synthetic analyses and verify scores vary (debug breakdown when DJANGO_DEBUG=1).

Usage (from repo root, after backend deps installed):
  set PYTHONPATH=backend\\src
  set DJANGO_SETTINGS_MODULE=config.settings
  set DJANGO_DEBUG=1
  python ml/scripts/run_ai_real_upgrade_smoke.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_DEBUG", "1")

import django

django.setup()

from apps.analysis.application.inference.orchestrator import analyze_resume  # noqa: E402


def main() -> None:
    seeds = [
        {
            "data": {
                "summary": "",
                "contact": {},
                "experiences": [],
                "educations": [],
                "skills": [],
                "languages": [],
            }
        },
        {
            "data": {
                "summary": "Estagiário em TI, primeiro estágio.",
                "contact": {},
                "experiences": [],
                "educations": [{"course": "ADS"}],
                "skills": [{"name": "Excel"}],
                "languages": [],
            }
        },
        {
            "data": {
                "summary": (
                    "Desenvolvedor sênior full-stack com 10 anos, líder de tecnologia, "
                    "Python Django React."
                ),
                "targetPosition": "Tech Lead",
                "contact": {},
                "experiences": [
                    {
                        "company": "Acme",
                        "position": "Staff Engineer",
                        "description": ["Arquitetura", "mentoria", "roadmap técnico."],
                    }
                ],
                "educations": [{"course": "Computer Science"}],
                "skills": [{"name": "Python"}, {"name": "Django"}],
                "languages": [],
            }
        },
        {
            "data": {
                "summary": "Engenheiro de dados. ETL, Airflow, SQL, 5 anos.",
                "targetPosition": "Engenheiro de dados sênior",
                "contact": {},
                "experiences": [
                    {
                        "company": "DataCo",
                        "position": "Data Engineer",
                        "description": ["Pipelines", "Spark", "monitoramento."],
                    }
                ],
                "educations": [],
                "skills": [{"name": "SQL"}, {"name": "Python"}],
                "languages": [],
            }
        },
        {
            "data": {
                "summary": "Product manager. Discovery, roadmap, stakeholders.",
                "targetPosition": "Product Manager",
                "contact": {},
                "experiences": [
                    {
                        "company": "SaaS Inc",
                        "position": "PM",
                        "description": ["OKRs", "discovery", "launch."],
                    }
                ],
                "educations": [],
                "skills": [{"name": "Agile"}],
                "languages": [],
            }
        },
    ]
    scores: list[int] = []
    for i, resume_data in enumerate(seeds):
        r = analyze_resume(resume_data, job_description_text=None, language="pt-BR")
        s = int(r.get("score") or 0)
        scores.append(s)
        dbg = (r.get("payload_json") or {}).get("debug") or {}
        br = (dbg.get("scoreBreakdown") or {}) if dbg else {}
        print(f"--- seed {i} overall={s} seniority={r.get('seniority_final_label')!r} ---")
        if br:
            print("scoreBreakdown:", br)
    unique = len(set(scores))
    print(f"unique overall scores: {unique} / {len(scores)} -> {scores}")
    if unique < 2:
        raise SystemExit("Expected score variation across seeds (>=2 distinct values).")
    print("OK")


if __name__ == "__main__":
    main()
