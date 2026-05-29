import json
import logging
from crewai.tools import BaseTool
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

class DuckDuckGoSearchTool(BaseTool):
    name: str = "DuckDuckGo Search"
    description: str = (
        "Выполняет поиск в интернете с помощью DuckDuckGo. "
        "Полезен для поиска новостей, тендеров, сайтов организаций и контактной информации. "
        "Параметр: query (строка поискового запроса). Возвращает: JSON-список результатов (заголовок, ссылка, текст)."
    )

    def _run(self, query: str) -> str:
        try:
            with DDGS() as ddgs:
                results = []
                # Use text() to fetch web results
                for r in ddgs.text(query, max_results=10):
                    results.append({
                        "title": r.get("title", ""),
                        "link": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
                return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error in DuckDuckGoSearchTool: {str(e)}")
            return f"Ошибка поиска: {str(e)}"
