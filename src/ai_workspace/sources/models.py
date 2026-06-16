"""Data models for the source reputation system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class CredibilityLevel(str, Enum):
    """Traffic-light credibility levels (following CRED-1 convention)."""

    LOW = "low"          # ≤ 0.20 — high credibility risk
    MIXED = "mixed"      # 0.21–0.50 — unreliable or mixed signals
    OK = "ok"            # > 0.50 — generally reliable
    NEUTRAL = "neutral"  # not found in dataset — unknown (not trustworthy)
    NONE = "none"        # no score computed yet


@dataclass
class SourceRecord:
    """Tracks a single source (URL) used in research."""

    url: str
    domain: str
    title: str = ""
    snippet: str = ""

    # Credibility scores (0.0-1.0)
    cred1_score: Optional[float] = None       # From CRED-1 dataset
    credinet_credible: Optional[bool] = None   # From CrediNet API
    our_score: Optional[float] = None          # Our computed score
    cross_ref_score: Optional[float] = None    # Cross-reference agreement

    # Usage tracking
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    times_used: int = 1
    times_accurate: int = 0
    times_inaccurate: int = 0

    # User feedback (-1 to 1)
    user_rating: Optional[float] = None

    # Metadata
    category: Optional[str] = None       # From CRED-1: fake, unreliable, conspiracy, etc.
    sources_flagging: int = 0             # How many independent lists flagged this domain
    is_flagged: bool = False              # Whether this source has been flagged

    @property
    def credibility_level(self) -> CredibilityLevel:
        """Traffic-light based on our best available score."""
        score = self.our_score or self.cred1_score
        if score is None:
            return CredibilityLevel.NEUTRAL
        if score <= 0.20:
            return CredibilityLevel.LOW
        if score <= 0.50:
            return CredibilityLevel.MIXED
        return CredibilityLevel.OK

    @property
    def effective_score(self) -> float:
        """Best available score, defaulting to neutral (0.5)."""
        if self.our_score is not None:
            return self.our_score
        if self.cred1_score is not None:
            return self.cred1_score
        return 0.5

    def merge(self, other: SourceRecord) -> None:
        """Merge data from another record of the same URL."""
        if other.title:
            self.title = other.title
        if other.snippet:
            self.snippet = other.snippet
        self.times_used += other.times_used
        self.times_accurate += other.times_accurate
        self.times_inaccurate += other.times_inaccurate
        self.last_seen = other.last_seen or datetime.utcnow()


@dataclass
class DomainReputation:
    """Aggregated reputation for an entire domain."""

    domain: str

    # External scores
    cred1_score: Optional[float] = None
    cred1_category: Optional[str] = None
    credinet_credible: Optional[bool] = None

    # Our tracked metrics
    times_used: int = 0
    times_accurate: int = 0
    times_inaccurate: int = 0
    accuracy_rate: Optional[float] = None  # times_accurate / times_used

    # User feedback
    user_rating: Optional[float] = None
    user_flags: int = 0

    # Computed
    composite_score: Optional[float] = None

    @property
    def credibility_level(self) -> CredibilityLevel:
        if self.composite_score is None:
            return CredibilityLevel.NEUTRAL
        if self.composite_score <= 0.20:
            return CredibilityLevel.LOW
        if self.composite_score <= 0.50:
            return CredibilityLevel.MIXED
        return CredibilityLevel.OK


@dataclass
class ResearchCitation:
    """A citation used in a research result, with source tracking."""

    url: str
    domain: str
    snippet: str = ""
    relevance: float = 0.5         # How relevant this was to the answer
    was_used_in_report: bool = True # Whether it ended up in final report
    source_record: Optional[SourceRecord] = None
    assessment: Optional[SourceAssessment] = None


@dataclass
class SourceAssessment:
    """Full assessment of a source's credibility for display."""

    url: str
    domain: str
    score: float                    # 0.0-1.0
    level: CredibilityLevel          # Traffic-light
    category: Optional[str] = None  # fake, unreliable, etc.
    flags: list[str] = field(default_factory=list)
    explanation: str = ""

    signals: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "domain": self.domain,
            "score": round(self.score, 3),
            "level": self.level.value,
            "category": self.category,
            "flags": self.flags,
            "explanation": self.explanation,
            "signals": {k: round(v, 3) for k, v in self.signals.items()},
        }
