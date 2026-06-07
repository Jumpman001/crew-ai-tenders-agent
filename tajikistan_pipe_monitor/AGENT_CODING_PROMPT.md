# ПРОМПТ ДЛЯ АГЕНТА КОДИРОВАНИЯ — CrewAI Tender Monitor

## КОНТЕКСТ

Проект: `crew-ai-tenders-agent` / `tajikistan_pipe_monitor/`
GitHub: https://github.com/Jumpman001/crew-ai-tenders-agent
Архитектура задокументирована в `CLAUDE.md` — прочитай его первым делом.

Задача: **Доделать реальный рабочий код** для всех 6 агентов, 6 задач и 3 инструментов.
CLAUDE.md содержит полную спецификацию — используй её как единственный источник истины.

---

## ЧТО УЖЕ ЕСТЬ (НЕ ТРОГАТЬ)

- `CLAUDE.md` — полная спецификация (прочитай целиком перед началом)
- `src/models/tender.py` — Pydantic модель `Tender` (если есть — не изменяй)
- `src/tools/web_scraper.py` — `WebScraperTool` (если реализован)
- `src/tools/rss_reader.py` — `RssReaderTool` (если реализован)
- `.env.example` — переменные окружения

---

## ЧТО НУЖНО СДЕЛАТЬ

### 1. Проверить и дополнить src/models/tender.py
Убедиться что модель `Tender` соответствует спецификации в CLAUDE.md.
Если файла нет — создать по спецификации из CLAUDE.md раздел "PYDANTIC МОДЕЛЬ".

### 2. Реализовать все 6 агентов

Каждый агент в своём файле. Использовать `@CrewBase` декоратор или прямую инициализацию —
смотри по версии crewai в pyproject.toml.

**Критические правила LLM (экономия токенов):**
- Агенты 1–5: `llm="claude-haiku-4-5-20251001"`
- Агент 6 (ReportAgent): `llm="claude-sonnet-4-6"`
- Альтернатива через litellm: `llm="gemini/gemini-2.5-flash"`

**Критическое правило фильтрации (ДО вызова LLM):**
```python
# В ScoutAgent и PipeCheckerAgent — фильтровать КОДОМ, не LLM:
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
    """Фильтр ДО LLM — экономит токены.
    Возвращает (relevant: bool, reason: str).
    """
    text_lower = text.lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in text_lower:
            return False, f"excluded: {kw}"
    for kw in INCLUDE_KEYWORDS:
        if kw.lower() in text_lower:
            return True, f"matched: {kw}"
    # Общая релевантность — передаём LLM только если есть хоть что-то водное
    water_hints = ["water", "вод", "труб", "pipe", "ирриг", "канал"]
    if any(h in text_lower for h in water_hints):
        return True, "general_water_hint"
    return False, "no_match"
```

**Правило обрезки контекста (экономия токенов):**
```python
def truncate_for_llm(text: str, max_chars: int = 3000) -> str:
    """Передавай LLM только первые 3000 символов страницы.
    Заголовок + первый экран содержит 95% нужных данных.
    """
    return text[:max_chars] if len(text) > max_chars else text
```

### 3. Реализовать все 6 задач (src/tasks/)

Каждая задача должна:
- Иметь `description` с конкретными инструкциями (не общими фразами)
- Иметь `expected_output` с точным форматом JSON
- Иметь правильный `context=[...]` из предыдущих задач
- Использовать `output_pydantic=Tender` или `output_json=Tender` где применимо

**Важно для ScoutTask** — передавать агенту список URL явно, не надеяться что агент
"знает" источники из backstory:
```python
SOURCES_TEXT = """
Просканируй СТРОГО ЭТИ источники (все 10):
1. https://search.worldbank.org/api/v2/procnotices?format=json&project_ctry_code=TJ&rows=50
2. https://www.adb.org/rss/projects/tenders?country=TAJ
3. https://www.dgmarket.com/tenders/rss.do?countryId=TJ
4. https://wsip-1.tj/
5. https://www.mewr.tj/
6. https://tenders.tj/
7. https://efsd.org/en/purchases/
8. https://bgate.isdb.org/CPP/EN/SearchTender.aspx
9. https://ecepp.ebrd.com (поиск: Tajikistan water)
10. DuckDuckGo: "Tajikistan water pipeline tender 2025 2026 IFB GPN"
"""
```

### 4. Реализовать ExcelWriterTool (src/tools/excel_writer.py)

Это самый важный инструмент — его `_run()` сейчас `pass`.

Полная реализация с openpyxl:
```python
def _run(self, projects_json: str) -> str:
    from datetime import datetime
    import json, os
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    projects = json.loads(projects_json)
    wb = Workbook()
    ws = wb.active
    ws.title = "Реестр проектов"

    # --- Стили ---
    header_font = Font(name="Arial", size=10, bold=True)
    data_font = Font(name="Arial", size=9)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="top", wrap_text=True)

    STATUS_COLORS = {
        "Активен": "D4EDDA",
        "В исполнении": "D4EDDA",
        "Не объявлен": "D0E8FF",
        "Ожидает": "FFF3CD",
        "Подготовка": "FFE4CC",
        "HIGH": "F8D7DA",
        "MEDIUM": "FFF3CD",
    }

    # --- Строка 1: заголовок ---
    ws.merge_cells("A1:T1")
    ws["A1"] = "РЕЕСТР ПРОЕКТОВ — composite.tj / Барс"
    ws["A1"].font = Font(name="Arial", size=12, bold=True)
    ws["A1"].alignment = center

    # --- Строка 2: подзаголовок ---
    ws.merge_cells("A2:T2")
    ws["A2"] = f"Дата обновления: {datetime.now().strftime('%d.%m.%Y')}"
    ws["A2"].alignment = center

    # --- Строки 3-4: заголовки колонок ---
    COLUMNS = [
        ("A", "№", 5),
        ("B", "Название проекта", 50),
        ("C", "", 0),
        ("D", "Исп. агентство", 28),
        ("E", "Финансирующий", 20),
        ("F", "Статус", 18),
        ("G", "Срок", 15),
        ("H", "Мес.", 8),
        ("I", "Подрядчик", 25),
        ("J", "Бюджет (Барс) USD", 22),
        ("K", "Риски", 30),
        ("L", "Контакты", 35),
        ("M", "DN (мм)", 12),
        ("N", "Материал", 12),
        ("O", "Длина (км)", 10),
        ("P", "Метод", 12),
        ("Q", "Дата IFB", 13),
        ("R", "Дедлайн", 13),
        ("S", "Пригодность", 14),
        ("T", "Ссылка", 40),
    ]

    for col_letter, title, width in COLUMNS:
        cell = ws[f"{col_letter}3"]
        cell.value = title
        cell.font = header_font
        cell.alignment = center
        if width > 0:
            ws.column_dimensions[col_letter].width = width

    ws.row_dimensions[3].height = 30
    ws.freeze_panes = "A5"

    # --- Строки с 5: данные ---
    for i, p in enumerate(projects, start=1):
        row = i + 4
        urgency = p.get("urgency", "LOW")
        status = p.get("status", "")
        color = STATUS_COLORS.get(urgency, STATUS_COLORS.get(status, "FFFFFF"))
        fill = PatternFill("solid", fgColor=color)

        def cell(col, val):
            c = ws[f"{col}{row}"]
            c.value = val if val else "—"
            c.font = data_font
            c.alignment = left
            c.fill = fill

        ws.merge_cells(f"B{row}:C{row}")
        cell("A", i)
        cell("B", p.get("name"))
        cell("D", p.get("executing_agency"))
        cell("E", p.get("donor"))
        cell("F", p.get("status"))
        cell("G", p.get("period"))
        cell("H", p.get("duration_months"))
        cell("I", p.get("contractor"))
        cell("J", p.get("composite_share") or p.get("total_budget"))
        cell("K", p.get("risks"))
        cell("L", f"{p.get('contact_name','')} {p.get('contact_email','')} {p.get('contact_phone','')}".strip())
        cell("M", p.get("pipe_diameter_mm"))
        cell("N", p.get("pipe_material"))
        cell("O", p.get("pipe_length_km"))
        cell("P", p.get("procurement_method"))
        cell("Q", p.get("ifb_date"))
        cell("R", p.get("deadline_date"))
        cell("S", p.get("urgency"))
        cell("T", p.get("source_url"))

        ws.row_dimensions[row].height = 90

    # --- Сохранение ---
    os.makedirs("output", exist_ok=True)
    filename = f"output/tajikistan_pipe_registry_{datetime.now().strftime('%Y%m%d')}.xlsx"
    wb.save(filename)
    return f"Excel сохранён: {filename} ({len(projects)} проектов)"
```

### 5. Реализовать src/crew.py

Полная сборка `TajikistanPipeMonitor` с:
- Всеми 6 агентами
- Всеми 6 задачами
- `Process.hierarchical`
- `manager_agent` (Haiku)
- `memory=True`
- `max_rpm=10` (защита от rate limit)

### 6. Реализовать main.py

По спецификации из CLAUDE.md. Добавить:
```python
import logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
```

---

## КРИТИЧЕСКИЕ ОГРАНИЧЕНИЯ (не нарушать)

### Экономия токенов — ЭТО ГЛАВНОЕ

```
┌─────────────────────────────────────────────────────────────┐
│  КОНВЕЙЕР ОБРАБОТКИ ТЕНДЕРА:                                │
│                                                             │
│  Источник (HTML/RSS/JSON)                                   │
│       ↓                                                     │
│  [КОД] pre_filter() — жёсткие ключевые слова               │
│       ↓ (отсев ~70% нерелевантного)                         │
│  [КОД] truncate_for_llm(text, max_chars=3000)              │
│       ↓                                                     │
│  [LLM Haiku] Извлечение структурированных полей            │
│       ↓                                                     │
│  [КОД] Pydantic валидация                                   │
│       ↓                                                     │
│  [LLM Haiku] Только если нужна интерпретация               │
│       ↓                                                     │
│  [LLM Sonnet] Только финальный отчёт (ReportAgent)         │
└─────────────────────────────────────────────────────────────┘
```

### HTTP-запросы — всегда с защитой
```python
# Обязательно для ВСЕХ HTTP-запросов:
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))
# timeout=30
# ротация User-Agent через fake_useragent
```

### Никогда не парсить через LLM то, что можно парсить кодом
- Регулярные выражения для извлечения DN, бюджета, дат — кодом
- LLM только для интерпретации амбигвалентных описаний
- Пример: `re.findall(r'DN\s*(\d{3,4})', text)` — никогда не спрашивай LLM "какой диаметр?"

### Обработка ошибок — везде
```python
try:
    result = tool.run(url)
except Exception as e:
    logger.warning(f"Источник недоступен: {url} — {e}")
    continue  # не падать, продолжать
```

---

## ПОРЯДОК РЕАЛИЗАЦИИ

1. Прочитай `CLAUDE.md` целиком
2. Посмотри текущие файлы в `tajikistan_pipe_monitor/`
3. Реализуй в таком порядке:
   a. `src/models/tender.py` (фундамент)
   b. `src/tools/excel_writer.py` (критичный инструмент)
   c. `src/tools/web_scraper.py` и `rss_reader.py` (если не реализованы)
   d. `src/agents/` — все 6 агентов
   e. `src/tasks/` — все 6 задач
   f. `src/crew.py` — сборка
   g. `main.py` — точка входа
4. Проверь запуском: `python main.py`

---

## ТЕСТ РАБОТОСПОСОБНОСТИ

После реализации система должна:

1. `python main.py` — запускается без ошибок импорта
2. ScoutAgent обращается хотя бы к 3 источникам и возвращает список
3. PipeAgent фильтрует нерелевантные тендеры ДО вызова LLM
4. ExcelWriterTool создаёт реальный .xlsx файл
5. В `output/` появляется файл `tajikistan_pipe_registry_YYYYMMDD.xlsx`

---

## ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (.env)

```
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...          # опционально
MIN_PIPE_DIAMETER_MM=400
OUTPUT_DIR=output
LOG_LEVEL=INFO
```

---

## ВАЖНОЕ ПРИМЕЧАНИЕ ПО АРХИТЕКТУРЕ

Барс — подрядчик, участвует в тендерах напрямую.
composite.tj — поставщик GRP/FRP труб DN 400–3000 мм Барсу.

Цель системы: найти тендеры где нужны трубы DN ≥ 400 мм →
Барс участвует как подрядчик → закупает трубы у composite.tj.

В Excel колонка "Бюджет (Барс) USD" = оценка всего подрядного контракта,
"Доля composite.tj" = стоимость только труб (обычно 20–40% от бюджета).
