"""Deterministic scoring modules."""

from prediction_desk.scoring.resolution_risk import ResolutionRiskResult, score_resolution_risk
from prediction_desk.scoring.trust_verdict import build_trust_verdict

__all__ = ["ResolutionRiskResult", "build_trust_verdict", "score_resolution_risk"]
