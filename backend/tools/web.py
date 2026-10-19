from typing import List, Dict, Any
from abc import ABC, abstractmethod

class BaseSearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        pass

class DuckDuckGoProvider(BaseSearchProvider):
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        try:
            from ddgs import DDGS
            with DDGS() as ddgs_client:
                raw_results = list(ddgs_client.text(query, max_results=max_results))
                formatted = []
                for item in raw_results:
                    formatted.append({
                        "title": item.get("title", ""),
                        "url": item.get("href", ""),
                        "snippet": item.get("body", ""),
                        "domain": item.get("href", "").split("//")[-1].split("/")[0],
                    })
                return formatted
        except Exception as e:
            raise RuntimeError(f"Web search unavailable: {e}") from e

class MockSearchProvider(BaseSearchProvider):
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        return [
            {
                "title": f"Verified Knowledge: {query}",
                "url": "https://nova.ai/local-index",
                "snippet": f"Autonomous context retrieved for user query '{query}'.",
                "domain": "nova.ai",
            }
        ]

# Active modular provider (can be swapped at runtime)
active_search_provider: BaseSearchProvider = DuckDuckGoProvider()

def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Execute modular web search and return structured source cards and synthesized answer."""
    clean_query = query.strip()
    if not clean_query:
        return {"success": False, "query": "", "results": [], "error": "Query cannot be empty."}
    
    try:
        results = active_search_provider.search(clean_query, max_results=max_results)
        return {
            "success": True,
            "query": clean_query,
            "count": len(results),
            "results": results,
            "summary": f"Found {len(results)} search results for '{clean_query}'.",
        }
    except Exception as e:
        return {
            "success": False,
            "query": clean_query,
            "results": [],
            "error": str(e),
        }

