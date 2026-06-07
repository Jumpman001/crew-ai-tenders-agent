import json
import logging
from crewai.tools import BaseTool
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


class DuckDuckGoSearchTool(BaseTool):
    name: str = "DuckDuckGo Search"
    description: str = (
        "Поиск в интернете через DuckDuckGo. "
        "Параметр: query (строка). Возвращает: JSON-список результатов (title, link, snippet)."
    )

    def _run(self, query: str) -> str:
        try:
            with DDGS() as ddgs:
                results = []
                for r in ddgs.text(query, max_results=5):
                    results.append({
                        "title": r.get("title", ""),
                        "link": r.get("href", ""),
                        "snippet": r.get("body", "")[:200],
                    })
                return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            logger.error("DuckDuckGoSearchTool error: %s", e)
            return f"Ошибка поиска: {str(e)}"
