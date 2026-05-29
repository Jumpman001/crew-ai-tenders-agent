from crewai.tools import BaseTool
import logging
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class WebScraperTool(BaseTool):
    name: str = "Web Scraper"
    description: str = (
        "Загружает HTML-страницу и извлекает текстовый контент. "
        "Используй для страниц тендеров которые НЕ требуют JavaScript. "
        "Параметр: url (строка). Возвращает: текст страницы (до 8000 символов)."
    )

    def _run(self, url: str) -> str:
        ua = UserAgent(fallback="Mozilla/5.0")
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru,en;q=0.5",
        }
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        session.mount("http://", HTTPAdapter(max_retries=retries))
        try:
            r = session.get(url, headers=headers, timeout=30, allow_redirects=True)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)[:8000]
        except Exception as e:
            return f"Ошибка загрузки {url}: {str(e)}"
