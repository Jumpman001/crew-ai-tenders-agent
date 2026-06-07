from crewai.tools import BaseTool
import logging
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

INCLUDE_KEYWORDS = [
    "DN 400", "DN 500", "DN 600", "DN 700", "DN 800", "DN 900", "DN 1000",
    "DN 1200", "d=930", "d=560", "магистральный", "main pipeline",
    "водовод", "water main", "коллектор", "collector",
    "ирригацион", "irrigation", "мелиорация",
]

EXCLUDE_KEYWORDS = [
    "газопровод", "gas pipeline", "нефтепровод", "oil pipeline",
    "DN 50", "DN 63", "DN 75", "DN 90", "DN 110", "DN 160",
]


def pre_filter(text: str) -> tuple[bool, str]:
    t = text.lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in t:
            return False, f"excluded: {kw}"
    for kw in INCLUDE_KEYWORDS:
        if kw.lower() in t:
            return True, f"matched: {kw}"
    water_hints = ["water", "вод", "труб", "pipe", "ирриг", "канал"]
    if any(h in t for h in water_hints):
        return True, "general_water_hint"
    return False, "no_match"


class WebScraperTool(BaseTool):
    name: str = "Web Scraper"
    description: str = (
        "Загружает веб-страницу (с поддержкой JS) и извлекает ее контент в формате Markdown. "
        "Отлично справляется с защитой от ботов. "
        "Параметр: url (строка). Возвращает: текст страницы в Markdown (до 4000 символов)."
    )

    def _run(self, url: str) -> str:
        import os
        from firecrawl import FirecrawlApp
        api_key = os.environ.get("FIRECRAWL_API_KEY")
        
        if api_key and "your_" not in api_key:
            try:
                app = FirecrawlApp(api_key=api_key)
                result = app.scrape_url(url, params={'formats': ['markdown']})
                text = result.get('markdown', '')
                
                if text:
                    is_relevant, reason = pre_filter(text)
                    if not is_relevant:
                        return f"Страница не релевантна ({reason})."
                    # Возвращаем до 4000 символов Markdown, так как он чище и плотнее
                    return text[:4000]
            except Exception as e:
                logger.warning(f"Firecrawl scrape failed for {url}: {e}. Falling back to bs4.")
        
        # Fallback на старый метод (BeautifulSoup), если ключа нет или произошла ошибка
        ua = UserAgent(fallback="Mozilla/5.0")
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru,en;q=0.5",
        }
        session = requests.Session()
        retries = Retry(total=1, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        session.mount("http://", HTTPAdapter(max_retries=retries))
        try:
            r = session.get(url, headers=headers, timeout=8, allow_redirects=True)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)

            is_relevant, reason = pre_filter(text)
            if not is_relevant:
                return f"Страница не релевантна ({reason})."

            return text[:2000]
        except Exception as e:
            return f"Ошибка загрузки {url}: {str(e)}"
