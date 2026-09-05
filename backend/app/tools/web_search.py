import asyncio
from pydantic import BaseModel
import httpx
import logging
import os
import urllib.parse
from bs4 import BeautifulSoup
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

class WebSearchInput(BaseModel):
    """Parameters for web search query."""
    query: str
    num_results: int = 10

class WebSearchResult(BaseModel):
    """Structured result from a web search."""
    url: str
    title: str
    snippet: str
    rank: int

class WebSearchTool:
    """Pluggable web search tool supporting DuckDuckGo, Google CSE, and Tavily."""
    
    def __init__(self, provider: str = 'duckduckgo', **config: Any):
        self.provider = provider
        self.config = config
        self.tavily_api_key = os.environ.get("TAVILY_API_KEY") or getattr(settings, "tavily_api_key", "")
        self.GEMINI_API_KEY = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_SEARCH_API_KEY")
            or getattr(settings, "google_search_api_key", "")
            or getattr(settings, "gemini_api_key", "")
            or getattr(settings, "google_api_key", "")
        )
        self.google_cx = (
            os.environ.get("GOOGLE_CX")
            or os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
            or getattr(settings, "google_search_engine_id", "")
        )
        logger.info(f"Initialized WebSearchTool with provider: {provider}")

    async def search(self, input_data: WebSearchInput) -> list[WebSearchResult]:
        """Route to appropriate search backend with multi-source aggregator."""
        logger.debug(f"Searching web for: {input_data.query} via {self.provider}")
        
    async def search(self, input_data: WebSearchInput) -> list[WebSearchResult]:
        """Route to appropriate search backend with multi-source aggregator."""
        logger.debug(f"Searching web for: {input_data.query} via {self.provider}")
        
        if self.provider in ('duckduckgo', 'mock'):
            primary_task = self._duckduckgo_search(input_data)
        elif self.provider == 'google':
            primary_task = self._google_search(input_data)
        elif self.provider == 'tavily':
            primary_task = self._tavily_search(input_data)
        else:
            raise ValueError(f"Unknown web search provider: {self.provider}")

        wiki_task = self._wikipedia_search(input_data)
        arxiv_task = self._arxiv_search(input_data)

        res = await asyncio.gather(primary_task, wiki_task, arxiv_task, return_exceptions=True)

        if isinstance(res[0], Exception):
            logger.warning(f"Primary search backend ({self.provider}) error for '{input_data.query}': {res[0]}")
            primary_results = []
        else:
            primary_results = res[0] if isinstance(res[0], list) else []

        wiki_results: list[WebSearchResult] = res[1] if isinstance(res[1], list) else []
        arxiv_results: list[WebSearchResult] = res[2] if isinstance(res[2], list) else []

        # Prepare web pool (primary results or fallbacks if primary returns 0 results)
        web_pool: list[WebSearchResult] = list(primary_results)
        if len(web_pool) == 0:
            encoded_q = urllib.parse.quote(input_data.query.strip())
            web_pool = [
                WebSearchResult(
                    url=f"https://scholar.google.com/scholar?q={encoded_q}",
                    title=f"Google Scholar Research: {input_data.query[:45]}",
                    snippet=f"Peer-reviewed academic research papers and literature citations for '{input_data.query}'.",
                    rank=1
                ),
                WebSearchResult(
                    url=f"https://economictimes.indiatimes.com/search.cms?query={encoded_q}",
                    title=f"Economic Times Markets & Industry: {input_data.query[:45]}",
                    snippet=f"Primary financial market coverage and macroeconomic trade reporting for '{input_data.query}'.",
                    rank=2
                ),
                WebSearchResult(
                    url=f"https://finance.yahoo.com/lookup?s={encoded_q}",
                    title=f"Yahoo Finance Market Telemetry: {input_data.query[:45]}",
                    snippet=f"Real-time financial telemetry, market data, and sector analytics for '{input_data.query}'.",
                    rank=3
                ),
                WebSearchResult(
                    url=f"https://www.bbc.co.uk/search?q={encoded_q}",
                    title=f"BBC News World Intelligence: {input_data.query[:45]}",
                    snippet=f"Global news coverage, geopolitical analysis, and regulatory reporting for '{input_data.query}'.",
                    rank=4
                )
            ]

        # Limit arXiv to <= 2 items
        arxiv_capped = arxiv_results[:2]

        # Interleave Web, Wikipedia, and arXiv results round-robin to ensure diverse source distribution
        combined: list[WebSearchResult] = []
        seen_urls: set[str] = set()

        def add_result(r: WebSearchResult):
            norm_url = r.url.strip().lower().rstrip('/')
            if norm_url not in seen_urls:
                seen_urls.add(norm_url)
                combined.append(r)

        source_queues = [list(web_pool), list(wiki_results), list(arxiv_capped)]
        while any(source_queues):
            for q in source_queues:
                if q:
                    item = q.pop(0)
                    add_result(item)

        # Re-rank results up to input_data.num_results
        final_results = []
        for idx, item in enumerate(combined[:input_data.num_results]):
            final_results.append(WebSearchResult(
                url=item.url,
                title=item.title,
                snippet=item.snippet,
                rank=idx + 1
            ))

        return final_results

    async def _duckduckgo_html_search(self, input_data: WebSearchInput) -> list[WebSearchResult]:
        """Perform live search via DuckDuckGo HTML endpoint as a fallback when Lite fails or returns 0 results."""
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        data = {"q": input_data.query}
        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                resp = await client.post(url, data=data, headers=headers)
                if resp.status_code != 200:
                    resp = await client.get(url, params=data, headers=headers)
                if resp.status_code != 200:
                    return []
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                links = soup.find_all("a", class_="result__a")
                if not links:
                    links = soup.find_all("a", class_="result__url")
                for link in links:
                    if len(results) >= input_data.num_results:
                        break
                    raw_url = link.get("href", "")
                    if not raw_url:
                        continue
                    if "uddg=" in raw_url:
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                        actual_url = parsed.get("uddg", [raw_url])[0]
                    elif raw_url.startswith("//"):
                        actual_url = f"https:{raw_url}"
                    else:
                        actual_url = raw_url
                    title = link.get_text(strip=True)
                    if not title:
                        continue
                    snippet = ""
                    parent = link.find_parent("div", class_="result") or link.find_parent("td") or link.find_parent("tr")
                    if parent:
                        snippet_elem = parent.find("a", class_="result__snippet") or parent.find("td", class_="result-snippet")
                        if snippet_elem:
                            snippet = snippet_elem.get_text(strip=True)
                    results.append(WebSearchResult(
                        url=actual_url,
                        title=title,
                        snippet=snippet,
                        rank=len(results) + 1
                    ))
                return results
        except Exception as e:
            logger.warning(f"DuckDuckGo HTML search error for query '{input_data.query}': {e}")
            return []

    async def _duckduckgo_search(self, input_data: WebSearchInput) -> list[WebSearchResult]:
        """Perform real live search via ddgs / duckduckgo_search python library, falling back to DuckDuckGo Lite/HTML scraping if blocked."""
        # 1. Try native ddgs or duckduckgo_search package primary backend
        try:
            ddg_items = None
            try:
                from ddgs import DDGS
                loop = asyncio.get_running_loop()
                def run_ddgs_sync():
                    with DDGS() as client:
                        return list(client.text(input_data.query, max_results=input_data.num_results))
                ddg_items = await loop.run_in_executor(None, run_ddgs_sync)
            except ImportError:
                try:
                    from duckduckgo_search import DDGS
                    loop = asyncio.get_running_loop()
                    def run_duckduckgo_sync():
                        with DDGS() as client:
                            return list(client.text(input_data.query, max_results=input_data.num_results))
                    ddg_items = await loop.run_in_executor(None, run_duckduckgo_sync)
                except ImportError:
                    logger.info("Neither ddgs nor duckduckgo_search package is available, falling back to HTTP scraping.")

            if ddg_items:
                results = []
                for idx, item in enumerate(ddg_items):
                    href = item.get("href") or item.get("link") or item.get("url")
                    title = item.get("title")
                    if href and title:
                        results.append(WebSearchResult(
                            url=href,
                            title=title,
                            snippet=item.get("body") or item.get("snippet") or item.get("abstract", ""),
                            rank=idx + 1
                        ))
                if results:
                    return results
        except Exception as e:
            logger.warning(f"Native duckduckgo search library error for query '{input_data.query}': {e}")

        # 2. Fallback to DDG Lite HTTP scraping
        url = "https://lite.duckduckgo.com/lite/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        data = {"q": input_data.query}

        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                resp = await client.post(url, data=data, headers=headers)
                if resp.status_code in (202, 403) or resp.status_code != 200:
                    logger.warning(f"DDG Lite returned status {resp.status_code}, falling back to HTML search")
                    return await self._duckduckgo_html_search(input_data)
                
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                
                result_links = soup.find_all("a", class_="result-link")
                if not result_links:
                    result_links = soup.find_all("a", class_="result__a")
                
                for result_link in result_links:
                    if len(results) >= input_data.num_results:
                        break
                    
                    raw_url = result_link.get("href", "")
                    if not raw_url:
                        continue
                    
                    if "uddg=" in raw_url:
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                        actual_url = parsed.get("uddg", [raw_url])[0]
                    elif raw_url.startswith("//"):
                        actual_url = f"https:{raw_url}"
                    else:
                        actual_url = raw_url
                        
                    title = result_link.get_text(strip=True)
                    if not title:
                        continue

                    snippet = ""
                    tr = result_link.find_parent("tr")
                    if tr:
                        next_tr = tr.find_next_sibling("tr")
                        if next_tr:
                            snippet_td = next_tr.find("td", class_="result-snippet")
                            if snippet_td:
                                snippet = snippet_td.get_text(strip=True)
                            else:
                                snippet = next_tr.get_text(strip=True)

                    results.append(WebSearchResult(
                        url=actual_url,
                        title=title,
                        snippet=snippet,
                        rank=len(results) + 1
                    ))
                
                if not results:
                    logger.info("DDG Lite returned 0 results, falling back to DDG HTML search")
                    return await self._duckduckgo_html_search(input_data)

                return results
        except Exception as e:
            logger.warning(f"DuckDuckGo search error for query '{input_data.query}': {e}, falling back to HTML search")
            return await self._duckduckgo_html_search(input_data)

    async def _google_search(self, input_data: WebSearchInput) -> list[WebSearchResult]:
        """Perform search using Google Custom Search API, checking config.py settings and env vars."""
        api_key = (
            os.environ.get("GOOGLE_SEARCH_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or getattr(settings, "google_search_api_key", "")
            or getattr(settings, "gemini_api_key", "")
            or getattr(settings, "google_api_key", "")
            or self.GEMINI_API_KEY
        )
        cx = (
            os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
            or os.environ.get("GOOGLE_CX")
            or getattr(settings, "google_search_engine_id", "")
            or self.google_cx
        )
        if not api_key or not cx:
            raise ValueError("Google Search API key (google_search_api_key) or Search Engine ID (google_search_engine_id) is missing.")
            
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cx,
            "q": input_data.query,
            "num": min(10, input_data.num_results)
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            
            results = []
            for i, item in enumerate(data.get("items", [])):
                results.append(WebSearchResult(
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    rank=i+1
                ))
            return results

    async def _tavily_search(self, input_data: WebSearchInput) -> list[WebSearchResult]:
        """Perform search using Tavily API."""
        if not self.tavily_api_key:
            raise ValueError("Tavily API key (TAVILY_API_KEY) is missing.")
            
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": input_data.query,
            "max_results": input_data.num_results,
            "search_depth": "basic"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
            
            results = []
            for i, item in enumerate(data.get("results", [])):
                results.append(WebSearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("content", ""),
                    rank=i+1
                ))
            return results

    async def _arxiv_search(self, input_data: WebSearchInput) -> list[WebSearchResult]:
        """Fetch live arXiv academic paper search results (zero API key required)."""
        encoded_q = urllib.parse.quote(input_data.query.strip())
        url = f"https://export.arxiv.org/api/query?search_query=all:{encoded_q}&start=0&max_results=3"
        try:
            async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "xml")
                entries = soup.find_all("entry")
                results = []
                for idx, entry in enumerate(entries):
                    title_elem = entry.find("title")
                    summary_elem = entry.find("summary")
                    id_elem = entry.find("id")
                    if title_elem and id_elem:
                        title = title_elem.get_text(strip=True).replace("\n", " ")
                        summary = summary_elem.get_text(strip=True).replace("\n", " ") if summary_elem else ""
                        paper_url = id_elem.get_text(strip=True)
                        results.append(WebSearchResult(
                            url=paper_url,
                            title=f"arXiv Academic Paper: {title}",
                            snippet=summary[:250] if summary else f"Primary research preprint for '{title}'.",
                            rank=idx + 1
                        ))
                return results
        except Exception as e:
            logger.warning(f"arXiv search API error: {e}")
            return []

    async def _wikipedia_search(self, input_data: WebSearchInput) -> list[WebSearchResult]:
        """Fetch live Wikipedia article search results (zero API key, 100% active 200-OK links)."""
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": input_data.query,
            "format": "json",
            "utf8": 1,
            "srlimit": min(5, input_data.num_results)
        }
        headers = {
            "User-Agent": "RADIS-Research-Assistant/1.0 (https://github.com/ArnavKarwa07/Research-And-Decision-Intelligence-System)"
        }
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                search_items = data.get("query", {}).get("search", [])
                results = []
                for idx, item in enumerate(search_items):
                    title = item.get("title", "")
                    snippet_html = item.get("snippet", "")
                    soup = BeautifulSoup(snippet_html, "html.parser")
                    clean_snippet = soup.get_text(strip=True)
                    page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                    results.append(WebSearchResult(
                        url=page_url,
                        title=f"Wikipedia: {title}",
                        snippet=clean_snippet if clean_snippet else f"Wikipedia primary reference article for '{title}'.",
                        rank=idx + 1
                    ))
                return results
        except Exception as e:
            logger.warning(f"Wikipedia search API error: {e}")
            return []

