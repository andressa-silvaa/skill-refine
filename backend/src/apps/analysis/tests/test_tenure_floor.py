"""
O piso de senioridade por tempo de casa documentado.

Existe porque a sonda de texto e' so'-texto por decisao de projeto — ler os meses vale 1,6 ponto para
ela — e em curriculo escrito fora do estilo do corpus ela subestima **num sentido so'**: em 19
curriculos escritos a mao saiu mais baixa que a regra 12 vezes e mais alta zero, com `intern` em
carreiras de 9 a 12 anos.

O piso e' simetrico aos vetos: eles descem sobre evidencia AUSENTE, ele levanta sobre evidencia
PRESENTE. A ordem importa e esta' fixada aqui — o piso primeiro, o veto depois, para a seguranca ter
a ultima palavra.
"""
from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.analysis.application.inference.tasks.seniority.rule_based import (
    apply_tenure_floor,
    clamp_seniority_vetoes,
)
from apps.analysis.application.inference.signals.types import ResumeSignals


def _resume(months: int, bullets: int = 6, position: str = "Engenheira de Software") -> dict:
    start_year = 2026 - (months // 12)
    start_month = max(1, 12 - (months % 12))
    return {
        "data": {
            "summary": "Profissional com trajetoria documentada.",
            "experiences": [
                {
                    "company": "Empresa A",
                    "position": position,
                    "startDate": f"{start_year}-{start_month:02d}",
                    "isCurrent": True,
                    "description": [f"Entrega numero {i} com resultado medido." for i in range(bullets)],
                }
            ],
            "educations": [{"institution": "U", "course": "Computacao", "degree": "Bacharelado"}],
            "skills": [{"name": "Python"}],
        }
    }


def _signals(months: int, bullets: int, experiences: int = 1) -> ResumeSignals:
    return ResumeSignals(
        total_months_experience=months,
        effective_months_experience=months,
        experiences_count=experiences,
        bullets_count=bullets,
        has_current_role=True,
        months_in_current_role=months,
        has_internship_terms=False,
        has_leadership_terms=True,
        has_links=False,
        summary_char_count=120,
        skills_count=4,
        education_present=True,
        completeness_score=80,
        completeness_level="adequate",
        insufficient_data=False,
        reasons=(),
        word_count=200,
        language="pt-BR",
    )


class FloorLiftsWhatTenureSupportsTest(SimpleTestCase):
    def test_nine_years_is_not_junior(self):
        label, evidence = apply_tenure_floor("junior", _resume(111))
        self.assertEqual(label, "senior")
        self.assertEqual(evidence[0]["rule"], "never_below_documented_tenure")
        self.assertEqual(evidence[0]["from"], "junior")

    def test_four_years_in_one_role_floors_at_mid(self):
        # 36 meses e' o degrau de `mid` na politica; 60 ja' e' o de `senior`.
        label, _e = apply_tenure_floor("intern", _resume(40))
        self.assertEqual(label, "mid")

    def test_two_years_is_not_intern(self):
        label, _e = apply_tenure_floor("intern", _resume(26))
        self.assertEqual(label, "junior")

    def test_a_real_intern_stays_intern(self):
        label, evidence = apply_tenure_floor("intern", _resume(8))
        self.assertEqual(label, "intern")
        self.assertEqual(evidence, [])


class FloorNeverLowersTest(SimpleTestCase):
    """So' levanta. Rebaixar e' trabalho dos vetos, e sobre outro tipo de evidencia."""

    def test_a_higher_label_is_left_alone(self):
        label, evidence = apply_tenure_floor("senior", _resume(30))
        self.assertEqual(label, "senior")
        self.assertEqual(evidence, [])

    def test_an_internship_title_disables_the_floor(self):
        label, evidence = apply_tenure_floor("intern", _resume(80, position="Estagiario de TI"))
        self.assertEqual(label, "intern", "estagio longo nao promove ninguem")
        self.assertEqual(evidence, [])

    def test_an_unknown_label_is_left_alone(self):
        label, evidence = apply_tenure_floor("staff", _resume(120))
        self.assertEqual(label, "staff")
        self.assertEqual(evidence, [])


class VetoKeepsTheLastWordTest(SimpleTestCase):
    """
    O piso levanta sobre evidencia presente; o veto desce sobre evidencia ausente. Aplicados nessa
    ordem, um curriculo de muitos meses mas poucos bullets sobe e volta — e o que sai e' a leitura
    conservadora, nao a otimista.
    """

    def test_floor_then_veto_lands_on_mid_when_bullets_are_few(self):
        lifted, _e = apply_tenure_floor("intern", _resume(150, bullets=5))
        self.assertEqual(lifted, "senior")
        final, veto = clamp_seniority_vetoes(lifted, _signals(150, bullets=5))
        self.assertEqual(final, "mid")
        self.assertEqual(veto[0]["rule"], "never_senior_few_bullets")

    def test_floor_then_veto_keeps_senior_when_evidence_is_there(self):
        lifted, _e = apply_tenure_floor("junior", _resume(150, bullets=8))
        final, veto = clamp_seniority_vetoes(lifted, _signals(150, bullets=8))
        self.assertEqual(final, "senior")
        self.assertEqual(veto, [])


class WhoeverChangedTheLabelSignsItTest(SimpleTestCase):
    """
    ``seniority_label_source`` alimenta a tela de revisao interna. Enquanto dizia
    `text_seniority_probe` mesmo quando o piso trocara a resposta, atribuia ao modelo uma decisao que
    tinha sido de uma regra — e nos 20 curriculos escritos a mao o piso trocou 12, logo a atribuicao
    erraria na maioria. Estes testes prendem a assinatura.
    """

    def _resolve(self, probe_label: str, resume: dict, signals: ResumeSignals) -> dict:
        from apps.analysis.application.inference import resolve_seniority as mod

        prediction = {
            "label": probe_label,
            "confidence": "high",
            "probs": {probe_label: 0.9},
            "source": "probe",
        }
        with (
            patch.object(mod, "get_seniority_probe_bundle", return_value=object()),
            patch.object(mod, "predict_text_seniority", return_value=prediction),
            patch.object(
                mod,
                "probe_metadata_for_task",
                return_value={"metadata": {}, "provider": "text_seniority_probe"},
            ),
        ):
            return mod._resolve_seniority(
                resume_data=resume,
                resume_text="texto",
                lang="pt-BR",
                config={
                    "multilang": False,
                    "require_model_answer": True,
                },
                rs=signals,
                encoder=object(),
            )

    def test_the_probe_signs_alone_when_no_rule_touched_the_answer(self):
        out = self._resolve("senior", _resume(111, bullets=8), _signals(111, bullets=8))
        self.assertEqual(out["final_label"], "senior")
        self.assertEqual(out["seniority_label_source"], "text_seniority_probe")

    def test_the_floor_signs_when_it_lifts_the_answer(self):
        out = self._resolve("junior", _resume(111, bullets=8), _signals(111, bullets=8))
        self.assertEqual(out["final_label"], "senior")
        self.assertEqual(out["seniority_label_source"], "probe+floor")

    def test_both_sign_when_the_floor_lifts_and_the_veto_lowers(self):
        out = self._resolve("intern", _resume(150, bullets=5), _signals(150, bullets=5))
        self.assertEqual(out["final_label"], "mid")
        self.assertEqual(out["seniority_label_source"], "probe+floor+veto")
