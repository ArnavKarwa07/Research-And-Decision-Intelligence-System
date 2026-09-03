import logging
import hashlib
from typing import Any, Literal
from pydantic import BaseModel
from app.agents.base import BaseAgent, AgentConfig, StepResult
from app.agents.agent_contracts import FactCheckInput, FactCheckOutput, RawSnippet, SourceMetadata
from app.agents.llm_provider import Message

logger = logging.getLogger(__name__)

class SearchStrategyResult(BaseModel):
    queries: list[str]

class VerdictResult(BaseModel):
    verdict: Literal['verified', 'disputed', 'refuted', 'insufficient_evidence']
    confidence_adjustment: float

class FactCheckAgent(BaseAgent):
    """
    FactCheckAgent per AGENT_CONTRACTS.md.
    Responsibilities:
    - 3 search strategies: Direct claim, Authority, Counter-evidence
    - Extract content and analyze for support/conflict
    - Strict Source Deduplication (URL + content hash)
    - Output verdict and confidence_adjustment
    """
    
    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                max_steps=20,
                max_tokens=50_000,
                timeout_seconds=300,
                allowed_tools=['web_search', 'extract_content']
            )
        super().__init__(config, agent_type="fact_check")
        self.internal_state = {
            'phase': 'init', # init -> plan_searches -> search -> extract -> analyze -> done
            'claim': None,
            'existing_source_urls': set(),
            'seen_content_hashes': set(),
            'search_queries': [],
            'search_results': [],
            'extracted_contents': [],
            'supporting_evidence': [],
            'conflicting_evidence': [],
            'new_sources': [],
            'verdict': 'insufficient_evidence',
            'confidence_adjustment': 1.0,
        }

    async def step(self, input_data: dict[str, Any]) -> StepResult:
        try:
            phase = self.internal_state['phase']
            
            if phase == 'init':
                typed_in = FactCheckInput(**input_data)
                self.internal_state['claim'] = typed_in.claim
                self.internal_state['existing_source_urls'] = {u.strip().lower().rstrip("/") for u in typed_in.existing_source_urls}
                self.internal_state['phase'] = 'plan_searches'
                return StepResult(action="init", message="Initialized FactCheckAgent state.")
                
            elif phase == 'plan_searches':
                return await self._plan_searches()
                
            elif phase == 'search':
                return await self._run_search()
                
            elif phase == 'extract':
                return await self._run_extraction()
                
            elif phase == 'analyze':
                return await self._run_analysis()
                
            else:
                return StepResult(action="idle", should_continue=False, message="Unknown phase.")
                
        except Exception as e:
            logger.error(f"FactCheckAgent error in step: {e}", exc_info=True)
            return StepResult(action="error", should_continue=False, message=str(e))

    async def _plan_searches(self) -> StepResult:
        claim_text = self.internal_state['claim'].text
        
        if not self._llm_provider:
            # Fallback if no LLM provider
            direct = claim_text
            auth = f"{claim_text} site:.gov OR site:.edu OR site:.org"
            counter = f"{claim_text} (fake OR false OR debunked OR hoax)"
            self.internal_state['search_queries'] = [direct, auth, counter]
        else:
            messages = [
                Message(role="system", content="Generate exactly 3 search queries for this claim: 1. Direct search 2. Authority search (append site:.gov OR site:.edu) 3. Counter-evidence search (append terms like debunked, false, etc.)."),
                Message(role="user", content=claim_text)
            ]
            res = await self._llm_provider.generate_structured(messages, SearchStrategyResult)
            self.internal_state['search_queries'] = res.queries[:3]
            
        self.internal_state['phase'] = 'search'
        return StepResult(action="plan_searches", message="Planned 3 search strategies.")

    async def _run_search(self) -> StepResult:
        if not self.internal_state['search_queries']:
            self.internal_state['phase'] = 'extract'
            return StepResult(action="search_complete", message="All searches completed.")
            
        query = self.internal_state['search_queries'].pop(0)
        
        retries = 3
        last_error = ""
        for attempt in range(retries):
            res = await self.call_tool("web_search", {"query": query, "num_results": 3})
            if res.success:
                for item in res.data:
                    url = getattr(item, "url", item.get("url") if isinstance(item, dict) else None)
                    if url:
                        norm_url = url.strip().lower().rstrip("/")
                        if norm_url not in self.internal_state['existing_source_urls']:
                            self.internal_state['search_results'].append({
                                "url": url,
                                "title": getattr(item, "title", item.get("title", "")) if isinstance(item, dict) or hasattr(item, "title") else "",
                                "query_used": query
                            })
                            self.internal_state['existing_source_urls'].add(norm_url)
                return StepResult(action="search", message=f"Searched: {query}")
            else:
                last_error = res.error
                logger.warning(f"Search failed (attempt {attempt+1}): {res.error}")
                
        return StepResult(action="search_failed", message=f"Failed search: {query}. Error: {last_error}")

    async def _run_extraction(self) -> StepResult:
        if not self.internal_state['search_results']:
            self.internal_state['phase'] = 'analyze'
            return StepResult(action="extract_complete", message="All extractions completed.")
            
        item = self.internal_state['search_results'].pop(0)
        url = item['url']
        
        res = await self.call_tool("extract_content", {"url": url})
        if res.success:
            text = getattr(res.data, "text", res.data.get("text") if isinstance(res.data, dict) else str(res.data))
            content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
            
            # Deduplication by content hash
            if content_hash not in self.internal_state['seen_content_hashes']:
                self.internal_state['seen_content_hashes'].add(content_hash)
                self.internal_state['extracted_contents'].append({
                    "url": url,
                    "title": item['title'],
                    "text": text,
                    "query_used": item['query_used']
                })
                return StepResult(action="extract", message=f"Extracted unique content from: {url}")
            else:
                return StepResult(action="extract_duplicate", message=f"Duplicate content hash skipped for: {url}")
        else:
            return StepResult(action="extract_failed", message=f"Failed extract: {url}")

    async def _run_analysis(self) -> StepResult:
        if not self.internal_state['extracted_contents']:
            self.internal_state['phase'] = 'done'
            
            # Final determination of verdict
            sup = len(self.internal_state['supporting_evidence'])
            con = len(self.internal_state['conflicting_evidence'])
            
            if sup > 0 and con == 0:
                self.internal_state['verdict'] = 'verified'
                self.internal_state['confidence_adjustment'] = 1.2
            elif con > 0 and sup == 0:
                self.internal_state['verdict'] = 'refuted'
                self.internal_state['confidence_adjustment'] = 0.5
            elif sup > 0 and con > 0:
                self.internal_state['verdict'] = 'disputed'
                self.internal_state['confidence_adjustment'] = 0.8
            else:
                self.internal_state['verdict'] = 'insufficient_evidence'
                self.internal_state['confidence_adjustment'] = 1.0

            return StepResult(action="analyze_complete", should_continue=False, message="Analysis complete.")
            
        item = self.internal_state['extracted_contents'].pop(0)
        
        # In a real implementation we would use LLM to analyze the excerpt, here we do a simple heuristic
        # or LLM check if provider is available
        text = item['text']
        claim_text = self.internal_state['claim'].text
        
        is_support = False
        is_conflict = False
        
        if self._llm_provider:
            messages = [
                Message(role="system", content="Determine if the provided text supports or refutes the claim. Return verdict='verified' for support, 'refuted' for conflict, or 'insufficient_evidence' otherwise. Always set confidence_adjustment."),
                Message(role="user", content=f"Claim: {claim_text}\n\nText: {text}")
            ]
            try:
                res = await self._llm_provider.generate_structured(messages, VerdictResult)
                if res.verdict == 'verified':
                    is_support = True
                elif res.verdict == 'refuted':
                    is_conflict = True
            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}")
                # fallback
                if claim_text.lower() in text.lower():
                    is_support = True
        else:
            if claim_text.lower() in text.lower():
                is_support = True

        src_meta = SourceMetadata(url=item['url'], title=item['title'])
        snippet = RawSnippet(content=text[:500], source=src_meta, query_used=item['query_used'])
        
        if is_support:
            self.internal_state['supporting_evidence'].append(snippet)
            self.internal_state['new_sources'].append(src_meta)
        elif is_conflict:
            self.internal_state['conflicting_evidence'].append(snippet)
            self.internal_state['new_sources'].append(src_meta)
            
        return StepResult(action="analyze", message=f"Analyzed {item['url']}")

    async def compile_output(self) -> dict[str, Any]:
        """Return FactCheckOutput dumped to dict."""
        output = FactCheckOutput(
            verdict=self.internal_state['verdict'],
            confidence_adjustment=self.internal_state['confidence_adjustment'],
            new_sources=self.internal_state['new_sources'],
            supporting_evidence=self.internal_state['supporting_evidence'],
            conflicting_evidence=self.internal_state['conflicting_evidence']
        )
        return output.model_dump()
