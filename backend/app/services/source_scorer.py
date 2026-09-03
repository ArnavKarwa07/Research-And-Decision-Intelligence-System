"""Source scoring services."""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import urllib.parse
from app.models.source import Source

class SourceScorer:
    """Service for calculating source credibility, freshness and independence."""
    
    @staticmethod
    def calculate_credibility(
        domain_authority: float,
        source_type: str,
        recency_days: float,
        cross_ref_count: int,
        is_independent: bool
    ) -> float:
        """
        Calculates source credibility score between 0.0 and 1.0.
        """
        # Base from domain authority (0-1)
        score = domain_authority
        
        # Source type multipliers
        type_multipliers = {
            "academic": 1.2,
            "official": 1.1,
            "news": 1.0,
            "blog": 0.8,
            "social": 0.5
        }
        score *= type_multipliers.get(source_type.lower() if source_type else "", 1.0)
        
        # Recency decay (if applicable)
        if recency_days > 365:
            score *= 0.9
        
        # Cross reference bonus
        if cross_ref_count > 0:
            score += min(cross_ref_count * 0.05, 0.2)
            
        # Independence bonus
        if is_independent:
            score *= 1.1
            
        return max(0.0, min(1.0, score))

    @staticmethod
    def classify_freshness(published_at: Optional[datetime], topic_volatility: str = "medium") -> str:
        """
        Classifies freshness based on publish date and topic volatility.
        Returns: FRESH (<30d), RECENT (30-90d), AGING (90-365d), STALE (>365d), ARCHIVAL.
        """
        if not published_at:
            return "ARCHIVAL"
            
        now = datetime.now(timezone.utc)
        
        # Ensure published_at is timezone-aware for subtraction
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
            
        days_old = max(0, (now - published_at).days)
        
        # Adjust thresholds based on volatility
        volatility_factor = 1.0
        if topic_volatility == "high":
            volatility_factor = 0.5
        elif topic_volatility == "low":
            volatility_factor = 2.0
            
        if days_old < 30 * volatility_factor:
            return "FRESH"
        elif days_old < 90 * volatility_factor:
            return "RECENT"
        elif days_old < 365 * volatility_factor:
            return "AGING"
        elif days_old > 365 * 5:
            return "ARCHIVAL"
        else:
            return "STALE"

    @staticmethod
    def classify_independence_groups(sources: List[Source]) -> Dict[str, List[Source]]:
        """
        Groups sources by independence factors like domain, content_hash (syndicated), wire service patterns.
        """
        groups: Dict[str, List[Source]] = {}
        
        for source in sources:
            # Determine grouping key
            group_key = "unknown"
            
            if source.content_hash:
                group_key = f"hash_{source.content_hash}"
            elif source.url:
                try:
                    parsed = urllib.parse.urlparse(source.url)
                    if parsed.netloc:
                        group_key = f"domain_{parsed.netloc}"
                except Exception:
                    pass
                    
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(source)
            
        return groups
