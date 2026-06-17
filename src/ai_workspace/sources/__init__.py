"""Source reputation system for AI Workspace.

Tracks, evaluates, and ranks information sources based on:
- Domain-level credibility (CRED-1 dataset, CrediNet)
- Empirical tracking (how often sources proved accurate)
- Cross-reference consistency (agreement between sources)
- User feedback (explicit ratings)
"""

from ai_workspace.core.sources import (
    SourceReputationService,
    extract_domain,
)
from ai_workspace.sources.models import (
    SourceRecord,
    DomainReputation,
    SourceAssessment,
    ResearchCitation,
    CredibilityLevel,
)

__all__ = [
    "SourceReputationService",
    "extract_domain",
    "SourceRecord",
    "DomainReputation",
    "SourceAssessment",
    "ResearchCitation",
    "CredibilityLevel",
]
