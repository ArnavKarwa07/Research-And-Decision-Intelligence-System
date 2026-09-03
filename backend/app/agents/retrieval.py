"""Retrieval Agent implementation for RADIS.
Handles RAG operations over internal documents and knowledge base chunks.
"""
import logging
from typing import Any, Dict
from app.agents.base import BaseAgent, AgentConfig, StepResult
from app.agents.agent_contracts import RetrievalAgentInput, RetrievalAgentOutput, DocumentChunk

logger = logging.getLogger(__name__)


class RetrievalAgent(BaseAgent):
    """Retrieval Agent responsible for semantic and keyword searches over internal project knowledge."""

    def __init__(self, config: AgentConfig):
        super().__init__(config, agent_type="Retrieval Agent")
        self.retrieved_chunks: list[DocumentChunk] = []

    async def step(self, input_data: Dict[str, Any]) -> StepResult:
        query = input_data.get("query", "")
        top_k = input_data.get("top_k", 5)

        logger.info(f"[Retrieval Agent] Searching internal knowledge base for: {query}")

        # Simulate or call internal knowledge retrieval tool
        chunks = [
            DocumentChunk(
                chunk_id=f"chunk-{i+1}",
                document_id="doc-internal-ref-001",
                content=f"Internal repository knowledge excerpt {i+1} regarding '{query}'. Architecture follows decoupled multi-agent standards.",
                score=round(0.95 - (i * 0.05), 2),
                metadata={"section": "Architecture Overview", "page": i + 1}
            )
            for i in range(min(top_k, 3))
        ]

        self.retrieved_chunks.extend(chunks)

        return StepResult(
            action="vector_search",
            result=[c.model_dump() for c in chunks],
            tokens_used=120,
            should_continue=False,
            message=f"Retrieved {len(chunks)} internal document chunks with top score {chunks[0].score if chunks else 0.0}."
        )

    async def compile_output(self) -> Dict[str, Any]:
        output = RetrievalAgentOutput(
            chunks=self.retrieved_chunks,
            query_used=self.state.progress_messages[0] if self.state.progress_messages else "",
            total_retrieved=len(self.retrieved_chunks)
        )
        return output.model_dump()
