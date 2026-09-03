from pydantic import BaseModel
import httpx
import logging
import os
import urllib.parse
from bs4 import BeautifulSoup
from typing import Any

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
        self.tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
        self.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
        self.google_cx = os.environ.get("GOOGLE_CX", "")
        logger.info(f"Initialized WebSearchTool with provider: {provider}")

    async def search(self, input_data: WebSearchInput) -> list[WebSearchResult]:
        """Route to appropriate search backend."""
        logger.debug(f"Searching web for: {input_data.query} via {self.provider}")
        
        if self.provider == 'duckduckgo' or self.provider == 'mock':
            return await self._duckduckgo_search(input_data)
        elif self.provider == 'google':
            return await self._google_search(input_data)
        elif self.provider == 'tavily':
            return await self._tavily_search(input_data)
        else:
            raise ValueError(f"Unknown web search provider: {self.provider}")

    async def _duckduckgo_search(self, input_data: WebSearchInput) -> list[WebSearchResult]:
        """Perform real live search via DuckDuckGo HTML endpoint (zero API key required)."""
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        data = {"q": input_data.query}

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.post(url, data=data, headers=headers)
                resp.raise_for_status()
                
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                
                for i, result in enumerate(soup.find_all("div", class_="result")):
                    if len(results) >= input_data.num_results:
                        break
                    
                    title_elem = result.find("a", class_="result__a")
                    snippet_elem = result.find("a", class_="result__snippet")
                    
                    if title_elem and title_elem.get("href"):
                        raw_url = title_elem["href"]
                        # Extract actual URL from DuckDuckGo redirect link if needed
                        if "uddg=" in raw_url:
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                            actual_url = parsed.get("uddg", [raw_url])[0]
                        else:
                            actual_url = raw_url
                            
                        results.append(WebSearchResult(
                            url=actual_url,
                            title=title_elem.get_text(strip=True),
                            snippet=snippet_elem.get_text(strip=True) if snippet_elem else "",
                            rank=len(results) + 1
                        ))
                
                return results
        except Exception as e:
            logger.error(f"DuckDuckGo search error for query '{input_data.query}': {e}")
            raise RuntimeError(f"Web search failed for query '{input_data.query}': {str(e)}")

    async def _google_search(self, input_data: WebSearchInput) -> list[WebSearchResult]:
        """Perform search using Google Custom Search API."""
        if not self.GEMINI_API_KEY or not self.google_cx:
            raise ValueError("Google Search API key (GEMINI_API_KEY) or Search Engine ID (GOOGLE_CX) is missing.")
            
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.GEMINI_API_KEY,
            "cx": self.google_cx,
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
