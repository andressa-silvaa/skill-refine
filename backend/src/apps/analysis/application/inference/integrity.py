"""
Which pillars were answered by a model, and what the analysis is allowed to do when one was not.

The project's rule is that no decision may be a heuristic except as a fallback. A fallback that
returns a score indistinguishable from the model's answer defeats that rule in practice: nobody
reading the response can tell which one answered, so the provider table stops being evidence. This
module makes the distinction explicit and enforceable.

Three states, not two:

* **model** — a trained head decided.
* **degraded** — a rule decided, and the response says so. Allowed only where the rule is a
  defensible answer on its own. Measured: ``rule_based_seniority`` reaches 70.4% against the probe's
  75.9% on held-out occupations, so it is a real degraded mode.
* **refused** — no answer. Used where the fallback carries almost no information, so returning a
  number would be worse than returning nothing. Measured: ``_heuristic_score`` averages 41.4 / 52.4 /
  57.8 across resumes planted as poor / fair / good — nearly flat on the very axis it claims to score,
  while carrying 78% of the final score.

``ANALYSIS_REQUIRE_MODEL_ANSWER`` selects between refusing and serving the heuristic. It defaults to
on, and is turned off in exactly one place: the golden snapshot suite, which exists to freeze the
fallback's behaviour so that code stays correct even though it no longer serves users. Fallback code
should remain tested; it should not remain served.
"""
from __future__ import annotations

from typing import Any

HEURISTIC_PROVIDERS = frozenset(
    {"heuristics", "heuristics-only", "rule_policy", "target_fit_policy", "domain_keywords", "local"}
)

# Pillars that may answer with a rule and still publish a score, provided the response is marked.
DEGRADABLE_TASKS = frozenset({"seniority"})


class ModelAnswerRequired(RuntimeError):
    """
    Raised when a pillar that must be model-driven had no model available.

    The worker turns this into a failed analysis with a readable reason. Failing is the point: the
    alternative is publishing a heuristic score that looks exactly like a model score.
    """

    def __init__(self, task: str, provider: str, detail: str = "") -> None:
        self.task = task
        self.provider = provider
        message = (
            f"{task} has no model answer (provider={provider or 'none'}). "
            "The bundle is missing or failed to load, and this pillar is not allowed to fall back to "
            "a heuristic. Check ANALYSIS_QUALITY_PROBE_ENABLED, ANALYSIS_EMBEDDINGS_ENABLED and the "
            "bundle under ANALYSIS_MODEL_ROOT."
        )
        super().__init__(f"{message} {detail}".strip())


def is_heuristic(provider: str | None) -> bool:
    return str(provider or "").strip() in HEURISTIC_PROVIDERS


def build_integrity_block(providers_by_task: dict[str, str]) -> dict[str, Any]:
    """
    Summarise which pillars are model-driven, for the response and for telemetry.

    Emitted on every analysis, degraded or not: a field that only appears when something is wrong is
    a field consumers forget to check.
    """
    degraded = sorted(task for task, provider in providers_by_task.items() if is_heuristic(provider))
    return {
        "degraded": bool(degraded),
        "degradedTasks": degraded,
        "providersByTask": dict(sorted(providers_by_task.items())),
        "reason": (
            "one or more pillars were answered by a rule rather than a trained model"
            if degraded
            else ""
        ),
    }
