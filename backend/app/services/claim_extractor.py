import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.models.claim import Claim
from app.models.claim_source import ClaimSource
from app.agents.agent_contracts import ClaimType
from app.agents.llm_provider import get_llm_provider, Message
from app.services.confidence_engine import ConfidenceEngine

logger = logging.getLogger(__name__)

class AtomicClaimExtraction(BaseModel):
    text: str = Field(description="The atomic claim extracted from the text.")
    claim_type: ClaimType = Field(description="The classification of the claim.")

class ClaimExtractionResult(BaseModel):
    claims: List[AtomicClaimExtraction]

class ClaimExtractor:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.llm = get_llm_provider()

    async def extract_claims(self, text: str, query_id: uuid.UUID, agent_run_id: Optional[uuid.UUID] = None) -> List[Claim]:
        messages = [
            Message(role="system", content="Extract atomic claims from the text. For each claim, provide the text and its type (FACT, CALCULATION, INFERENCE, ASSUMPTION, PREDICTION, OPINION, UNRESOLVED)."),
            Message(role="user", content=text)
        ]
        
        result = await self.llm.generate_structured(messages, ClaimExtractionResult)
        
        extracted_claims = []
        try:
            for c in result.claims:
                confidence = ConfidenceEngine.calculate_from_sources(c.claim_type.value, [])
                claim = Claim(
                    query_id=query_id,
                    content=c.text,
                    claim_type=c.claim_type.value,
                    confidence=confidence,
                    status="unverified",
                    created_by_agent_run_id=agent_run_id
                )
                self.db.add(claim)
                extracted_claims.append(claim)
                
            await self.db.commit()
            for claim in extracted_claims:
                await self.db.refresh(claim)
        except Exception:
            await self.db.rollback()
            raise
            
        return extracted_claims

    async def link_provenance(self, claim: Claim, source_snippets: List[Dict[str, Any]]) -> List[ClaimSource]:
        """
        source_snippets: List of dicts, e.g. [{"source_id": "...", "content": "..."}]
        """
        claim_sources = []
        try:
            for snippet in source_snippets:
                content = snippet.get("content", "")
                source_id_str = snippet.get("source_id")
                if not content or not source_id_str:
                    continue
                    
                idx = content.find(claim.content)
                if idx != -1:
                    excerpt = claim.content
                    location = {"startChar": idx, "endChar": idx + len(claim.content), "paragraph": 0, "found": True}
                    relevance = 0.9
                    
                    cs = ClaimSource(
                        claim_id=claim.id,
                        source_id=uuid.UUID(source_id_str) if isinstance(source_id_str, str) else source_id_str,
                        excerpt=excerpt,
                        excerpt_location=location,
                        support_type="SUPPORTED",
                        relevance_score=relevance
                    )
                    self.db.add(cs)
                    claim_sources.append(cs)
                elif claim.content.lower() in content.lower():
                    # Excerpt not found exactly, but found in lowercase
                    excerpt = claim.content
                    location = {"startChar": 0, "endChar": 0, "paragraph": 0, "found": False}
                    relevance = 0.7
                    
                    cs = ClaimSource(
                        claim_id=claim.id,
                        source_id=uuid.UUID(source_id_str) if isinstance(source_id_str, str) else source_id_str,
                        excerpt=excerpt,
                        excerpt_location=location,
                        support_type="SUPPORTED",
                        relevance_score=relevance
                    )
                    self.db.add(cs)
                    claim_sources.append(cs)
            
            if claim_sources:
                await self.db.commit()
                for cs in claim_sources:
                    await self.db.refresh(cs)
        except Exception:
            await self.db.rollback()
            raise
            
        return claim_sources
