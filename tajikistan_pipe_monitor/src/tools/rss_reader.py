from crewai.tools import BaseTool
import feedparser

class RssReaderTool(BaseTool):
    name: str = "RSS Reader"
    description: str = (
        "Читает RSS/Atom фид и возвращает список записей. "
        "Используй для ADB (adb.org/rss/...) и DGMarket RSS. "
        "Параметр: rss_url (строка). Возвращает: JSON список статей."
    )

    def _run(self, rss_url: str) -> str:
        import json
        try:
            feed = feedparser.parse(rss_url)
            entries = []
            for e in feed.entries[:30]:
                entries.append({
                    "title": e.get("title", ""),
                    "link": e.get("link", ""),
                    "summary": e.get("summary", "")[:300],
                    "published": e.get("published", ""),
                })
            return json.dumps(entries, ensure_ascii=False)
        except Exception as ex:
            return f"Ошибка чтения RSS {rss_url}: {str(ex)}"
