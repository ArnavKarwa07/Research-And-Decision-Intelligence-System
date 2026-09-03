"""Confidence calculation engine."""

class ConfidenceEngine:
    """Engine for calculating claim confidence."""
    
    BASE_TYPE_WEIGHTS = {
        "FACT": 0.9,
        "CALCULATION": 0.85,
        "INFERENCE": 0.6,
        "ASSUMPTION": 0.4,
        "PREDICTION": 0.3,
        "OPINION": 0.2,
        "UNRESOLVED": 0.1
    }
    
    @classmethod
    def calculate_from_sources(cls, claim_type: str, supporting_sources: list) -> float:
        if not supporting_sources:
            return 0.5
        avg_credibility = sum(getattr(s, "relevance_score", 0.5) for s in supporting_sources) / len(supporting_sources)
        return cls.calculate(claim_type, avg_credibility)

    @classmethod
    def calculate(
        cls,
        claim_type: str,
        source_credibility_avg: float,
        independence_factor: float = 1.0,
        recency_factor: float = 1.0,
        verification_bonus: float = 1.0
    ) -> float:
        """
        Calculates claim confidence.
        Formula: confidence = base_type_weight * source_credibility_avg * independence_factor * recency_factor * verification_bonus
        Clamped between 0.0 and 1.0.
        """
        if claim_type is None:
            claim_type = "UNRESOLVED"
            
        base_weight = cls.BASE_TYPE_WEIGHTS.get(claim_type.upper(), 0.1)
        
        confidence = (
            base_weight *
            source_credibility_avg *
            independence_factor *
            recency_factor *
            verification_bonus
        )
        
        return max(0.0, min(1.0, confidence))
