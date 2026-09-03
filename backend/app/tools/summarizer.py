from pydantic import BaseModel, Field
import logging
from typing import Any
from ..agents.llm_provider import LLMProvider, Message

logger = logging.getLogger(__name__)

class SummaryInput(BaseModel):
    """Input for summarizer tool."""
    content: str
    objective: str
    max_length: int = 500

class Summary(BaseModel):
    """Structured output from summarizer tool."""
    text: str
    key_points: list[str] = Field(description="List of core facts extracted")
    relevance_score: float = Field(description="Score from 0.0 to 1.0 indicating relevance to objective")

class SummarizerTool:
    """Uses LLM to summarize content based on an objective."""
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def summarize(self, input_data: SummaryInput) -> Summary:
        """Use LLM to summarize content relative to the research objective."""
        logger.debug(f"Summarizing text (length {len(input_data.content)}) for objective: {input_data.objective}")
        
        # Truncate aggressively for context window if needed, rough heuristic
        max_chars = 30000 
        content = input_data.content
        if len(content) > max_chars:
            content = content[:max_chars] + "... [TRUNCATED]"
            
        system_prompt = (
            "You are a precise research summarizer. Your goal is to analyze the provided text "
            "and extract information strictly relevant to the provided objective. "
            "Do not invent facts. Return a structured JSON summary."
        )
        
        user_prompt = f"Objective: {input_data.objective}\n\nContent:\n{content}"
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        try:
            summary = await self.llm_provider.generate_structured(
                messages=messages,
                response_schema=Summary,
                timeout=60.0
            )
            # Truncate text output if requested
            if len(summary.text) > input_data.max_length:
                summary.text = summary.text[:input_data.max_length] + "..."
            return summary
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return Summary(
                text=f"Failed to summarize: {str(e)}",
                key_points=[],
                relevance_score=0.0
            )
