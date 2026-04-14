"""Target fit, domain inference, and conservative target seniority (generalist)."""
from __future__ import annotations

import unittest

from apps.analysis.application.inference.resume_mapper import resume_to_text
from apps.analysis.application.inference.target_fit import (
    compute_career_switch,
    compute_target_fit_policy,
    compute_target_seniority,
    extract_target_fit_signals,
    heuristic_target_fit_score,
    infer_domain_category,
)
from apps.analysis.application.inference.target_fit.fit_signals import TargetFitSignals


class DomainInferenceTest(unittest.TestCase):
    def test_nurse_pt(self):
        r = infer_domain_category("Enfermeiro hospitalar", "pt-BR")
        self.assertEqual(r["domainCategory"], "health")
        self.assertGreater(len(r["evidenceTokens"]), 0)

    def test_developer_not_only_tech_keyword(self):
        r = infer_domain_category("Desenvolvedor Full Stack", "pt-BR")
        self.assertEqual(r["domainCategory"], "technology")

    def test_teacher_es(self):
        r = infer_domain_category("Profesor de matemáticas", "es-ES")
        self.assertEqual(r["domainCategory"], "education")

    def test_empty_is_general(self):
        r = infer_domain_category("", "en-US")
        self.assertEqual(r["domainCategory"], "general")


def _bio_resume_data() -> dict:
    return {
        "data": {
            "targetPosition": "",
            "summary": "Bióloga com 10 anos de pesquisa em ecologia e laboratório.",
            "skills": [{"name": "PCR"}, {"name": "Ecologia"}, {"name": "Estatística"}],
            "experiences": [
                {
                    "company": "USP",
                    "position": "Pesquisadora",
                    "description": ["Campo", "Análise de dados ecológicos", "Publicações"],
                }
            ],
            "educations": [{"course": "Biologia", "degree": "Mestrado", "institution": "Universidade"}],
            "contact": {},
        }
    }


def _finance_resume_data() -> dict:
    return {
        "data": {
            "targetPosition": "",
            "summary": "Analista financeiro com 5 anos em FP&A e orçamento.",
            "skills": [{"name": "Excel"}, {"name": "Orçamento"}, {"name": "Power BI"}],
            "experiences": [
                {
                    "company": "ACME",
                    "position": "Analista Financeiro",
                    "description": ["Forecast", "Budget", "Reporting"],
                }
            ],
            "educations": [{"course": "Administração", "degree": "Graduação", "institution": "FGV"}],
            "contact": {"linkedin": "https://linkedin.com/in/x"},
        }
    }


def _domains_for(resume: dict, target: str, lang: str) -> tuple[str, str]:
    txt = resume_to_text(resume, language=lang).full_text
    rd = infer_domain_category(txt[:12000], lang=lang)
    td = infer_domain_category(target, lang=lang)
    return str(rd["domainCategory"]), str(td["domainCategory"])


class TargetFitScenariosTest(unittest.TestCase):
    def test_biologist_to_developer_low_target_seniority(self):
        resume = _bio_resume_data()
        resume["data"]["targetPosition"] = "Desenvolvedor(a) Full Stack"
        target = "Desenvolvedor(a) Full Stack"
        sig = extract_target_fit_signals(resume, target, None, "pt-BR", completeness_score=72)
        rd, td = _domains_for(resume, target, "pt-BR")
        score = heuristic_target_fit_score(sig, has_job_text=False, resume_domain=rd, target_domain=td)
        self.assertLess(score, 55)
        pack = compute_target_seniority("senior", score, sig, "pt-BR")
        self.assertIn(pack["targetSeniorityLabel"], ("intern", "junior"))

    def test_biologist_to_senior_biologist_high_fit(self):
        resume = _bio_resume_data()
        target = "Bióloga Sênior"
        resume["data"]["targetPosition"] = target
        sig = extract_target_fit_signals(resume, target, None, "pt-BR", completeness_score=80)
        rd, td = _domains_for(resume, target, "pt-BR")
        score = heuristic_target_fit_score(sig, has_job_text=False, resume_domain=rd, target_domain=td)
        self.assertGreaterEqual(score, 40)
        pack = compute_target_seniority("senior", score, sig, "pt-BR")
        self.assertIn(pack["targetSeniorityLabel"], ("mid", "senior"))

    def test_finance_to_finance(self):
        resume = _finance_resume_data()
        target = "Analista Financeiro Pleno"
        resume["data"]["targetPosition"] = target
        sig = extract_target_fit_signals(
            resume, target, "Orçamento forecast FP&A", "pt-BR", completeness_score=78
        )
        rd, td = _domains_for(resume, target, "pt-BR")
        score = heuristic_target_fit_score(sig, has_job_text=True, resume_domain=rd, target_domain=td)
        self.assertGreaterEqual(score, 50)
        pack = compute_target_seniority("mid", score, sig, "pt-BR")
        self.assertIn(pack["targetSeniorityLabel"], ("mid", "senior", "junior"))

    def test_finance_to_ux_career_switch(self):
        resume = _finance_resume_data()
        target = "UX Designer"
        resume["data"]["targetPosition"] = target
        sig = extract_target_fit_signals(resume, target, None, "pt-BR", completeness_score=70)
        rd, td = _domains_for(resume, target, "pt-BR")
        score = heuristic_target_fit_score(sig, has_job_text=False, resume_domain=rd, target_domain=td)
        cs = compute_career_switch("mid", score, rd, td)
        self.assertTrue(cs["detected"] or score < 50)


class ClampRulesTest(unittest.TestCase):
    def test_no_experience_hits_caps_junior(self):
        sig = TargetFitSignals(
            required_terms_total=6,
            required_terms_hit=4,
            experience_keyword_hits=0,
            portfolio_evidence=False,
            skills_hit=3,
        )
        pack = compute_target_seniority("senior", 85, sig, "en-US")
        self.assertEqual(pack["targetSeniorityLabel"], "junior")


class PolicyAliasTest(unittest.TestCase):
    def test_compute_target_fit_policy_matches_heuristic(self):
        sig = TargetFitSignals(
            required_terms_total=10,
            required_terms_hit=5,
            skills_total=10,
            skills_hit=2,
            experience_keyword_hits=2,
            education_alignment="medium",
            portfolio_evidence=False,
            completeness_score=65,
        )
        h = heuristic_target_fit_score(
            sig, has_job_text=False, resume_domain="finance", target_domain="technology"
        )
        p = compute_target_fit_policy(
            sig, has_job_text=False, resume_domain="finance", target_domain="technology"
        )
        self.assertEqual(h, p)
