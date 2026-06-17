"""Resolution corpus parser, scoring, diffing, and service APIs."""

from prediction_desk.resolution.ambiguity import assess_rule_ambiguity
from prediction_desk.resolution.diff import diff_rule_snapshots
from prediction_desk.resolution.enums import (
    Comparator,
    ParseStatus,
    PredicateType,
    ResolutionSourceType,
    RuleSemanticChangeFlag,
)
from prediction_desk.resolution.models import (
    AmbiguityAssessment,
    EvidenceSpan,
    ResolutionAnalysis,
    ResolutionPredicate,
    ResolutionSource,
    RuleSnapshotDiff,
)
from prediction_desk.resolution.parser import parse_resolution_predicate
from prediction_desk.resolution.service import ResolutionCorpusService

__all__ = [
    "AmbiguityAssessment",
    "Comparator",
    "EvidenceSpan",
    "ParseStatus",
    "PredicateType",
    "ResolutionAnalysis",
    "ResolutionCorpusService",
    "ResolutionPredicate",
    "ResolutionSource",
    "ResolutionSourceType",
    "RuleSemanticChangeFlag",
    "RuleSnapshotDiff",
    "assess_rule_ambiguity",
    "diff_rule_snapshots",
    "parse_resolution_predicate",
]
