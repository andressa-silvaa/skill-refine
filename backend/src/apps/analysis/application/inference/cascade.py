"""
Shared cascade/fallback helper for inference tasks.

Canonizes try-step → capture failure → next-step without changing any task's
step order or success criteria. Each step returns CascadeResult | None;
the first applied result wins.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


@dataclass
class CascadeResult:
    value: Any
    provider: str
    status: str
    evidence: Any = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def applied(self) -> bool:
        return self.status == "applied"


StepFn = Callable[[], CascadeResult | None]


def run_cascade(
    steps: Iterable[StepFn],
    *,
    default: CascadeResult | None = None,
    stop_statuses: frozenset[str] = frozenset({"applied"}),
) -> CascadeResult:
    """
    Run cascade steps in order. Stops at the first result whose status is in
    stop_statuses (default: "applied"). Exceptions inside a step are converted
    to status="error" and the cascade continues.
    """
    last_error: CascadeResult | None = None
    last_skipped: CascadeResult | None = None
    for step in steps:
        try:
            result = step()
        except Exception as exc:  # noqa: BLE001 — cascade must not abort pipeline
            last_error = CascadeResult(
                value=None,
                provider="cascade",
                status="error",
                evidence={"error": str(exc)},
            )
            continue
        if result is None:
            continue
        if result.status in stop_statuses:
            return result
        if result.status == "error":
            last_error = result
        else:
            last_skipped = result
    if default is not None:
        return default
    if last_skipped is not None:
        return last_skipped
    if last_error is not None:
        return last_error
    return CascadeResult(value=None, provider="none", status="skipped_no_step")
