from typing import Any, Literal
from pydantic import BaseModel, Field
import logging
from .base import BaseAgent, AgentConfig, StepResult, AgentStatus
from .llm_provider import Message

logger = logging.getLogger(__name__)

class ResearchInput(BaseModel):
    search_queries: list[str]
    objectives: str
    depth: Literal['shallow', 'deep'] = 'shallow'

class EvidenceItem(BaseModel):
    claim: str
    source_url: str
    evidence_type: Literal['FACT', 'CALCULATION', 'INFERENCE', 'ASSUMPTION', 'PREDICTION', 'OPINION', 'UNRESOLVED']
    quality_score: float = Field(ge=0.0, le=1.0)

class ResearchOutput(BaseModel):
    evidence: list[EvidenceItem] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)

class ResearchAgent(BaseAgent):
    """
    Research Agent per AGENT_CONTRACTS.md.
    Responsibilities:
    - Execute searches
    - Extract content
    - Summarize & classify evidence
    Must handle tool failures gracefully (Rule 14) and distinguish evidence (Rule 6).
    """
    
    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                max_steps=20,
                max_tokens=50_000,
                timeout_seconds=300,
                allowed_tools=['web_search', 'extract_content', 'summarize']
            )
        super().__init__(config, agent_type="research")
        self.internal_state = {
            'queries_to_run': [],
            'objectives': '',
            'search_results': [],
            'extracted_contents': [],
            'evidence': [],
            'sources_tracked': set(),
            'phase': 'init'  # init -> search -> extract -> analyze -> done
        }

    async def step(self, input_data: dict[str, Any]) -> StepResult:
        try:
            if self.internal_state['phase'] == 'init':
                typed_in = ResearchInput(**input_data)
                self.internal_state['queries_to_run'] = typed_in.search_queries
                self.internal_state['objectives'] = typed_in.objectives
                self.internal_state['phase'] = 'search'
                return StepResult(action="init", message="Initialized research state.")
                
            phase = self.internal_state['phase']
            logger.info(f"ResearchAgent (ID: {self.state.agent_id}) phase: {phase}")
            
            if phase == 'search':
                return await self._run_search()
            elif phase == 'extract':
                return await self._run_extraction()
            elif phase == 'analyze':
                return await self._run_analysis()
            else:
                return StepResult(action="idle", should_continue=False, message="Unknown phase.")
                
        except Exception as e:
            logger.error(f"Research error in step: {e}", exc_info=True)
            return StepResult(action="error", should_continue=False, message=str(e))

    async def _run_search(self) -> StepResult:
        if not self.internal_state['queries_to_run']:
            self.internal_state['phase'] = 'extract'
            return StepResult(action="search_complete", message="All searches completed.")
            
        query = self.internal_state['queries_to_run'].pop(0)
        
        # Rule 14: Retry logic can be applied here for resilient tool calls
        retries = 3
        last_error = ""
        for attempt in range(retries):
            res = await self.call_tool("web_search", {"query": query, "num_results": 3})
            if res.success:
                for item in res.data:
                    url = item.url
                    if url not in self.internal_state['sources_tracked']:
                        self.internal_state['search_results'].append(url)
                        self.internal_state['sources_tracked'].add(url)
                return StepResult(action="search", message=f"Searched: {query}")
            else:
                last_error = res.error
                logger.warning(f"Search failed (attempt {attempt+1}): {res.error}")
                
        return StepResult(action="search_failed", message=f"Failed search: {query}. Error: {last_error}")

    async def _run_extraction(self) -> StepResult:
        if not self.internal_state['search_results']:
            self.internal_state['phase'] = 'analyze'
            return StepResult(action="extract_complete", message="All extractions completed.")
            
        url = self.internal_state['search_results'].pop(0)
        
        res = await self.call_tool("extract_content", {"url": url})
        if res.success and res.data.text:
            self.internal_state['extracted_contents'].append({
                "url": url,
                "text": res.data.text
            })
            return StepResult(action="extract", message=f"Extracted: {url}")
        else:
            return StepResult(action="extract_failed", message=f"Failed extract: {url}")

    async def _run_analysis(self) -> StepResult:
        if not self.internal_state['extracted_contents']:
            self.internal_state['phase'] = 'done'
            return StepResult(action="analyze_complete", should_continue=False, message="Analysis complete.")
            
        item = self.internal_state['extracted_contents'].pop(0)
        
        res = await self.call_tool("summarize", {
            "content": item["text"],
            "objective": self.internal_state['objectives']
        })
        
        if res.success:
            summary_data = res.data
            for pt in summary_data.key_points:
                # Rule 6: Classify evidence (Mocked classification here for brevity, in prod use LLM)
                ev_type = 'FACT' if 'is' in pt else 'INFERENCE' 
                self.internal_state['evidence'].append(EvidenceItem(
                    claim=pt,
                    source_url=item["url"],
                    evidence_type=ev_type,
                    quality_score=summary_data.relevance_score
                ))
            return StepResult(action="analyze", message=f"Analyzed {item['url']}")
        else:
            return StepResult(action="analyze_failed", message=f"Failed to analyze {item['url']}")

    async def compile_output(self) -> dict[str, Any]:
        """Return ResearchOutput dumped to dict."""
        output = ResearchOutput(
            evidence=self.internal_state['evidence'],
            sources=list(self.internal_state['sources_tracked'])
        )
        return output.model_dump()
