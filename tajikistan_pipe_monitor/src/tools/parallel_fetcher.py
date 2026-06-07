"""
Параллельный Python-фетчер — запускается ДО LLM-агентов.
Обходит все 10 источников одновременно (ThreadPoolExecutor, timeout=8s).
Возвращает текстовый список кандидатов без единого LLM-вызова.
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

WATER_KEYWORDS = [
    "water", "вод", "труб", "pipe", "ирриг", "canal", "канал",
    "мелиор", "sewage", "канализ", "водовод", "дренаж", "водоснаб",
    "irrigation", "pipeline", "водопровод",
]
EXCLUDE_KEYWORDS = [
    "газ", "gas pipeline", "нефт", "oil pipeline", "электр", "power supply",
]

SOURCES = [
    ("WB_API",   "https://search.worldbank.org/api/v2/procnotices?format=json&project_ctry_code=TJ&rows=50&status=active"),
    ("ADB_RSS",  "https://www.adb.org/rss/projects/tenders?country=TAJ"),
    ("DGM_RSS",  "https://www.dgmarket.com/tenders/rss.do?countryId=TJ"),
    ("EFSD",     "https://efsd.org/en/purchases/"),
    ("WSIP1",    "https://wsip-1.tj/"),
    ("MEWR",     "https://www.mewr.tj/"),
    ("TENDERS",  "https://tenders.tj/"),
    ("ISDB",     "https://www.isdb.org/project-procurement/tenders"),
    ("UN_TJ",    "https://tajikistan.un.org/en/jobs"),
    ("ISDB_BGT", "https://bgate.isdb.org/CPP/EN/SearchTender.aspx"),
]

_UA = UserAgent(fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")


def _is_relevant(text: str) -> bool:
    t = text.lower()
    if any(kw.lower() in t for kw in EXCLUDE_KEYWORDS):
        return False
    return any(kw.lower() in t for kw in WATER_KEYWORDS)


def _fetch_rss(name: str, url: str) -> list[dict]:
    try:
        feed = feedparser.parse(url)
        results = []
        for e in feed.entries[:25]:
            title = e.get("title", "")
            summary = e.get("summary", "")[:250]
            if _is_relevant(title + " " + summary):
                donor = "ADB" if "adb.org" in url else "DGMarket"
                results.append({
                    "title": title,
                    "url": e.get("link", ""),
                    "summary": summary,
                    "date": e.get("published", ""),
                    "source": name,
                    "donor": donor,
                })
        return results
    except Exception as ex:
        logger.warning("RSS %s: %s", name, ex)
        return []


def _fetch_wb_api(url: str) -> list[dict]:
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        data = r.json()
        results = []
        for notice in data.get("notices", [])[:40]:
            title = notice.get("noticeDesc", "") or notice.get("proj_name", "")
            project = notice.get("proj_name", "")
            combined = title + " " + project
            if _is_relevant(combined):
                results.append({
                    "title": title[:200],
                    "url": notice.get("url", ""),
                    "summary": project[:200],
                    "date": notice.get("noticedate", ""),
                    "source": "World Bank STEP",
                    "donor": "World Bank",
                })
        return results
    except Exception as ex:
        logger.warning("WB API: %s", ex)
        return []


def _fetch_html(name: str, url: str) -> list[dict]:
    headers = {
        "User-Agent": _UA.random,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru,en;q=0.5",
    }
    try:
        r = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        soup = BeautifulSoup(r.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Extract relevant anchor links first
        base = urlparse(url)
        candidates = []
        for a in soup.find_all("a", href=True)[:80]:
            link_text = a.get_text(strip=True)
            href = a["href"]
            if len(link_text) < 10:
                continue
            if not _is_relevant(link_text + " " + href):
                continue
            if href.startswith("http"):
                full_url = href
            elif href.startswith("/"):
                full_url = f"{base.scheme}://{base.netloc}{href}"
            else:
                continue
            candidates.append({
                "title": link_text[:200],
                "url": full_url,
                "summary": "",
                "date": "",
                "source": name,
                "donor": name,
            })

        # If no links found, use the page itself
        if not candidates:
            text = soup.get_text(separator=" ", strip=True)
            if _is_relevant(text):
                page_title = soup.title.string.strip() if soup.title and soup.title.string else name
                candidates.append({
                    "title": page_title[:200],
                    "url": url,
                    "summary": text[:300],
                    "date": "",
                    "source": name,
                    "donor": name,
                })

        return candidates[:6]
    except Exception as ex:
        logger.warning("HTML %s (%s): %s", name, url, ex)
        return []


def fetch_all_sources(max_candidates: int = 20) -> list[dict]:
    """Обходит все источники параллельно. Возвращает список кандидатов."""
    all_results: list[dict] = []

    def _dispatch(name: str, url: str) -> list[dict]:
        if "adb.org/rss" in url or "dgmarket.com/tenders/rss" in url:
            return _fetch_rss(name, url)
        if "worldbank.org/api" in url:
            return _fetch_wb_api(url)
        return _fetch_html(name, url)

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_dispatch, name, url): name for name, url in SOURCES}
        for fut in as_completed(futures):
            try:
                all_results.extend(fut.result())
            except Exception as ex:
                logger.warning("Fetch error: %s", ex)

    # Дедубликация по URL
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in all_results:
        u = item.get("url", "")
        if u and u not in seen:
            seen.add(u)
            deduped.append(item)

    limited = deduped[:max_candidates]
    logger.info("Pre-fetcher: %d уникальных кандидатов, возвращаем %d", len(deduped), len(limited))
    return limited


def format_for_prompt(candidates: list[dict]) -> str:
    """Форматирует список кандидатов в текст без фигурных скобок (безопасно для CrewAI format())."""
    if not candidates:
        return "Кандидаты не найдены. Используй DuckDuckGo для самостоятельного поиска."
    lines = []
    for i, c in enumerate(candidates, 1):
        title = c.get("title", "Без названия")
        url = c.get("url", "")
        donor = c.get("donor", c.get("source", ""))
        date = c.get("date", "")
        summary = c.get("summary", "")[:150]
        line = f"{i}. [{donor}] {title}"
        if date:
            line += f" | {date}"
        if url:
            line += f"\n   URL: {url}"
        if summary:
            line += f"\n   Описание: {summary}"
        lines.append(line)
    return "\n\n".join(lines)
