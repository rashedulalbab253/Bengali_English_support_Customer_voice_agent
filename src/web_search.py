"""
Web Search module using DuckDuckGo for grounding LLM responses with real-time information.
No API key required - completely free.
"""

import traceback
from typing import List, Dict
from src.utils import logger

try:
    from duckduckgo_search import DDGS
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False
    logger.warning("duckduckgo-search not installed. Web search grounding disabled.")


def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the web using DuckDuckGo and return results.
    
    Returns a list of dicts with keys: title, url, body
    """
    if not SEARCH_AVAILABLE:
        logger.warning("Web search unavailable - duckduckgo-search not installed")
        return []
    
    try:
        logger.info(f"Searching web for: {query}")
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        
        formatted = []
        for r in results:
            formatted.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "body": r.get("body", "")
            })
        
        logger.info(f"Found {len(formatted)} search results")
        return formatted
        
    except Exception as e:
        logger.error(f"Web search failed: {e}\n{traceback.format_exc()}")
        return []


def format_search_context(results: List[Dict[str, str]]) -> str:
    """
    Format search results into a context string for the LLM prompt.
    """
    if not results:
        return ""
    
    context_parts = ["[Web Search Results - Use this information to provide accurate, up-to-date answers]:"]
    for i, r in enumerate(results, 1):
        context_parts.append(f"\n--- Source {i}: {r['title']} ---")
        context_parts.append(f"URL: {r['url']}")
        context_parts.append(f"Content: {r['body']}")
    
    context_parts.append("\n[End of Search Results. Base your answer on the above information when relevant.]")
    return "\n".join(context_parts)


def needs_web_search(query: str) -> bool:
    """
    Heuristic to determine if a query likely needs web search for current information.
    Returns True if the query seems to be about current events, products, prices, etc.
    """
    query_lower = query.lower()
    
    # Keywords that suggest the need for current/real-time information
    search_indicators = [
        # Product queries
        "iphone", "samsung", "galaxy", "pixel", "macbook", "ipad",
        "laptop", "phone", "tablet", "airpods", "watch",
        # Price/availability
        "price", "cost", "how much", "available", "buy", "purchase",
        "release", "released", "launch", "launched", "new",
        "latest", "newest", "recent", "upcoming", "when",
        # Current events
        "today", "now", "current", "2024", "2025", "2026",
        # Comparison
        "vs", "versus", "compare", "better", "best",
        # Specs and reviews
        "specs", "specification", "review", "rating",
        "feature", "features", "benchmark",
        # Bengali keywords
        "দাম", "কত", "নতুন", "কিনতে", "কবে", "বের হয়েছে",
        "সর্বশেষ", "তুলনা", "ফিচার", "রিভিউ",
    ]
    
    return any(keyword in query_lower for keyword in search_indicators)
