from __future__ import annotations

from dataclasses import dataclass


RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    requires_approval: bool
    reason: str


def evaluate(risk_level: str, approved: bool = False) -> SafetyDecision:
    risk = risk_level.lower().strip()
    if risk not in RISK_ORDER:
        return SafetyDecision(False, False, f"unknown risk level: {risk_level}")
    if risk == "low":
        return SafetyDecision(True, False, "low-risk tool")
    if approved:
        return SafetyDecision(True, False, "approved")
    return SafetyDecision(False, True, f"{risk}-risk tool requires approval")
