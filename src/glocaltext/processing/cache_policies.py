"""Cache decision policies for determining which matches to cache."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from glocaltext.match_state import MatchLifecycle
from glocaltext.models import TextMatch

__all__ = [
    "CacheDecision",
    "CachePolicy",
    "CachePolicyChain",
    "SkippedMatchPolicy",
    "TranslatedMatchPolicy",
]

logger = logging.getLogger(__name__)


@dataclass
class CacheDecision:
    """
    Represents a cache decision with rationale.

    Attributes:
        should_cache: True to cache, False to skip, None to defer to next policy
        reason: Human-readable explanation for the decision

    """

    should_cache: bool | None
    reason: str


class CachePolicy(ABC):
    """Abstract base class for cache decision policies."""

    @abstractmethod
    def should_cache(self, match: TextMatch) -> CacheDecision:
        """
        Evaluate whether a match should be cached.

        Returns:
            CacheDecision with should_cache=True/False for definitive decision,
            or should_cache=None to defer to the next policy in the chain.

        """
        raise NotImplementedError


class TranslatedMatchPolicy(CachePolicy):
    """Policy for matches that were successfully translated via API."""

    def should_cache(self, match: TextMatch) -> CacheDecision:
        """Cache newly translated matches."""
        if match.lifecycle == MatchLifecycle.TRANSLATED:
            return CacheDecision(should_cache=True, reason="Newly translated via API")
        # Not applicable, defer to next policy
        return CacheDecision(should_cache=None, reason="Not a translated match")


class SkippedMatchPolicy(CachePolicy):
    """
    Policy for skipped matches based on skip_reason category.

    Cache Strategy:
    - optimization/validation skips: Cache (stable, performance-beneficial)
    - rule/mode skips: Don't cache (user rules may change, mode is transient)
    """

    def should_cache(self, match: TextMatch) -> CacheDecision:
        """Decide caching based on skip reason category."""
        if match.lifecycle != MatchLifecycle.SKIPPED:
            return CacheDecision(should_cache=None, reason="Not a skipped match")

        if not match.skip_reason:
            return CacheDecision(should_cache=False, reason="Skipped without reason - conservative no-cache")

        # Cache stable optimization/validation skips for performance
        if match.skip_reason.category in ("optimization", "validation"):
            return CacheDecision(should_cache=True, reason=f"Stable {match.skip_reason.category} skip: {match.skip_reason.code}")

        # Don't cache user rules (may change) or mode skips (transient)
        if match.skip_reason.category in ("rule", "mode"):
            return CacheDecision(should_cache=False, reason=f"Volatile {match.skip_reason.category} skip: {match.skip_reason.code}")

        # Unknown category - be conservative
        return CacheDecision(should_cache=False, reason=f"Unknown skip category: {match.skip_reason.category}")


class CachePolicyChain:
    """
    Chains multiple cache policies, evaluating them in order.

    The first policy to return a definitive decision (True/False) wins.
    If all policies return None, defaults to False (don't cache).
    """

    def __init__(self, policies: list[CachePolicy]) -> None:
        """Initialize the policy chain with a list of policies."""
        self.policies = policies

    def evaluate(self, match: TextMatch) -> CacheDecision:
        """Evaluate policies in order until a definitive decision is reached."""
        for policy in self.policies:
            decision = policy.should_cache(match)
            if decision.should_cache is not None:
                return decision

        # No policy matched - default to not caching
        return CacheDecision(should_cache=False, reason="No policy matched - default no-cache")
