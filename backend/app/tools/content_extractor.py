from pydantic import BaseModel
import httpx
import logging
from typing import Any
import re
import socket
import urllib.parse
import ipaddress
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

logger = logging.getLogger(__name__)

def is_safe_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local:
            return False
        if ip in ('127.0.0.1', '169.254.169.254'):
            return False
        return True
    except Exception:
        return False

class ExtractedContent(BaseModel):
    """Cleaned text content extracted from a URL."""
    url: str
    title: str
    text: str
    word_count: int
    extraction_method: str

async def extract_content(url: str, timeout: float = 10.0, max_length: int = 50000) -> ExtractedContent:
    """Fetch URL and extract clean text. Uses httpx + BeautifulSoup."""
    
    if not BeautifulSoup:
        logger.error("BeautifulSoup4 is not installed. Cannot extract content properly.")
        raise ImportError("beautifulsoup4 package is required for content_extractor")
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    logger.debug(f"Fetching content from URL: {url}")
    
    if not is_safe_url(url):
        raise ValueError("URL failed security check: untrusted target")
    
    async with httpx.AsyncClient(verify=True) as client:
        try:
            resp = await client.get(url, headers=headers, timeout=timeout, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return ExtractedContent(
                url=url,
                title="",
                text=f"Error fetching content: {e}",
                word_count=0,
                extraction_method="failed"
            )

    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract title
    title = soup.title.string if soup.title else ""
    title = title.strip() if title else ""
    
    # Remove unwanted tags
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]):
        element.decompose()
        
    # Heuristically find main content
    main_content = soup.find('main') or soup.find('article') or soup.find(id='content') or soup.body
    
    if not main_content:
        clean_text = soup.get_text(separator=' ')
    else:
        clean_text = main_content.get_text(separator=' ')
        
    # Clean up whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Truncate
    if len(clean_text) > max_length:
        clean_text = clean_text[:max_length] + "... [TRUNCATED]"
        
    word_count = len(clean_text.split())
    
    return ExtractedContent(
        url=url,
        title=title,
        text=clean_text,
        word_count=word_count,
        extraction_method="beautifulsoup"
    )
