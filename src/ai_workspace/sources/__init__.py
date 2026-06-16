"""Source reputation system for AI Workspace.

Tracks, evaluates, and ranks information sources based on:
- Domain-level credibility (CRED-1 dataset, CrediNet)
- Empirical tracking (how often sources proved accurate)
- Cross-reference consistency (agreement between sources)
- User feedback (explicit ratings)
- Temporal decay (older sources lose weight)
"""

from ai_workspace.sources.reputation import (
    SourceReputationManager,
    SourceReputationError,
)
from ai_workspace.sources.scoring import (
    compute_source_score,
    compute_domain_base_score,
    CrossReferenceScore,
)
from ai_workspace.sources.models import (
    SourceRecord,
    DomainReputation,
    SourceAssessment,
    ResearchCitation,
)

__all__ = [
    "SourceReputationManager",
    "SourceReputationError",
    "compute_source_score",
    "compute_domain_base_score",
    "CrossReferenceScore",
    "SourceRecord",
    "DomainReputation",
    "SourceAssessment",
    "ResearchCitation",
]
