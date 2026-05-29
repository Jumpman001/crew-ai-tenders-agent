# CLAUDE.md — CrewAI Tender Monitor: Таджикистан, Трубы DN ≥ 400 мм

## КОНТЕКСТ ПРОЕКТА

Ты пишешь код для **CrewAI**-агентов, которые автоматически ищут, анализируют и структурируют
информацию о проектах по **замене и прокладке трубопроводов** на территории Таджикистана.

Конечный результат — структурированный Excel/CSV реестр с полными данными по каждому проекту:
название, донор, исполнитель, подрядчик, бюджет, статус, сроки, контакты, ссылки.

**Два ключевых участника:**
- **composite.tj** — производитель стеклопластиковых (GRP/FRP) труб
  диаметром DN 400–3000 мм в Душанбе, Таджикистан.
- **Барс** — компания-подрядчик, которая участвует в тендерах на замену и прокладку
  трубопроводов и закупает трубы у composite.tj.

Цель системы: находить тендеры, в которых **Барс** может участвовать как подрядчик,
а **composite.tj** — поставить трубы GRP/FRP DN ≥ 400 мм.

---

## ТЕХНИЧЕСКИЙ СТЕК

```
python = "^3.11"
crewai = "^0.80.0"
crewai-tools = "^0.14.0"
openpyxl = "^3.1.0"              # генерация Excel
python-dotenv = "^1.0.0"
pydantic = "^2.0.0"
requests = "^2.31.0"
beautifulsoup4 = "^4.12.0"
feedparser = "^6.0.11"
lxml = "^5.0.0"                  # HTML-парсер для BeautifulSoup
fake-useragent = "^2.0.0"       # ротация User-Agent
duckduckgo-search = "^7.0.0"    # поиск без API-ключа
google-generativeai = "^0.8.0"  # Gemini LLM backend
litellm = "^1.40.0"             # унифицированный LLM-прокси (Anthropic + Gemini)
```

**LLM-провайдеры:** Anthropic (Claude) + Google (Gemini). Оба настраиваются через `.env`.

Модель для всех агентов: **`claude-haiku-4-5-20251001`** (экономия токенов).
Только финальный аналитик (ReportAgent) использует: **`claude-sonnet-4-6`**.
Альтернативный бэкенд: **`gemini/gemini-2.5-flash`** (через litellm).

---

## АРХИТЕКТУРА: 6 АГЕНТОВ + 1 МЕНЕДЖЕР

```
┌─────────────────────────────────────────────────────────────┐
│                    CrewAI Pipeline                          │
│                                                             │
│  [1] ScoutAgent      →  ищет новые тендеры по 10 источникам│
│  [2] DetailsAgent    →  углубляется в каждый найденный лот  │
│  [3] ContactAgent    →  находит контакты PMU/PIU            │
│  [4] PipeAgent       →  проверяет соответствие DN ≥ 400 мм  │
│  [5] RiskAgent       →  оценивает риски и сроки             │
│  [6] ReportAgent     →  собирает финальный Excel-реестр     │
│                                                             │
│  [M] ManagerAgent    →  координирует процесс (Process.hierarchical)│
└─────────────────────────────────────────────────────────────┘
```

---

## СТРУКТУРА ФАЙЛОВ (создавай именно такую)

```
tajikistan_pipe_monitor/
├── .env.example
├── pyproject.toml
├── README.md
├── main.py                    # точка входа
├── config/
│   ├── agents.yaml            # конфиги агентов
│   └── tasks.yaml             # конфиги задач
├── src/
│   ├── __init__.py
│   ├── crew.py                # сборка Crew
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── scout.py           # ScoutAgent
│   │   ├── details.py         # DetailsAgent
│   │   ├── contacts.py        # ContactAgent
│   │   ├── pipe_checker.py    # PipeAgent
│   │   ├── risk_analyst.py    # RiskAgent
│   │   └── reporter.py        # ReportAgent
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── scout_task.py
│   │   ├── details_task.py
│   │   ├── contact_task.py
│   │   ├── pipe_task.py
│   │   ├── risk_task.py
│   │   └── report_task.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── web_scraper.py     # кастомный скрапер сайтов доноров
│   │   ├── rss_reader.py      # RSS читалка (ADB, DGMarket)
│   │   └── excel_writer.py    # генератор Excel реестра
│   └── models/
│       ├── __init__.py
│       └── tender.py          # Pydantic модель тендера
└── output/
    └── .gitkeep
```

---

## PYDANTIC МОДЕЛЬ ТЕНДЕРА (src/models/tender.py)

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class Tender(BaseModel):
    """Полная модель тендера/проекта — соответствует колонкам Excel-реестра."""

    # Идентификация
    num: int = Field(description="Порядковый номер в реестре")
    project_id: Optional[str] = Field(None, description="ID проекта (P177325, TJK-1044 и т.д.)")
    lot_ref: Optional[str] = Field(None, description="Номер лота (WSIP-W-PMU/001 и т.д.)")

    # Основные данные
    name: str = Field(description="Полное название проекта/лота")
    donor: str = Field(description="Финансирующее учреждение (ВБ, АБР, ЕБРР, IsDB и т.д.)")
    grant_loan_no: Optional[str] = Field(None, description="Номер гранта/кредита")
    executing_agency: str = Field(description="Исполнительное агентство")
    piu_pmu: Optional[str] = Field(None, description="ПИУ/ПМУ — орган управления проектом")

    # Статус и сроки
    status: str = Field(description="Статус: Активен / В исполнении / Не объявлен / Подготовка / GPN")
    period: Optional[str] = Field(None, description="Срок реализации (напр. до 2027-07)")
    duration_months: Optional[int] = Field(None, description="Продолжительность в месяцах")
    ifb_date: Optional[str] = Field(None, description="Дата публикации IFB/GPN/SPN")
    deadline_date: Optional[str] = Field(None, description="Дата закрытия тендера")

    # Подрядчик и закупки
    contractor: Optional[str] = Field(None, description="Компания-подрядчик (если известна)")
    procurement_method: Optional[str] = Field(None, description="NCB / ICB / RFQ / Direct")
    procurement_rules: Optional[str] = Field(None, description="Правила закупок донора")

    # Финансы
    total_budget: Optional[str] = Field(None, description="Общий бюджет лота в USD/EUR")
    composite_share: Optional[str] = Field(None, description="Потенциальная доля composite.tj (трубы)")

    # Технические параметры труб
    pipe_diameter_mm: Optional[str] = Field(None, description="Диаметр труб DN, мм")
    pipe_material: Optional[str] = Field(None, description="Материал: ПЭ / ПВХ / сталь / ВЧШГ / GRP")
    pipe_length_km: Optional[float] = Field(None, description="Протяжённость трубопровода, км")
    pipe_pressure_class: Optional[str] = Field(None, description="Класс давления PN")
    dn_400_confirmed: bool = Field(False, description="Подтверждено DN ≥ 400 мм")

    # Регион
    region: Optional[str] = Field(None, description="Регион: Хатлон / Душанбе / Согд / ГБАО")
    district: Optional[str] = Field(None, description="Район")

    # Контакты
    contact_name: Optional[str] = Field(None, description="ФИО контактного лица")
    contact_org: Optional[str] = Field(None, description="Организация")
    contact_email: Optional[str] = Field(None, description="Email")
    contact_phone: Optional[str] = Field(None, description="Телефон")
    contact_address: Optional[str] = Field(None, description="Адрес")

    # Риски
    risks: Optional[str] = Field(None, description="Риски и проблемы")
    urgency: str = Field("LOW", description="Срочность: HIGH / MEDIUM / LOW")

    # Источники
    source_url: Optional[str] = Field(None, description="Ссылка на тендер")
    source_name: Optional[str] = Field(None, description="Название источника")
    last_updated: Optional[str] = Field(None, description="Дата последнего обновления")
```

---

## АГЕНТ 1 — ScoutAgent (src/agents/scout.py)

**Роль:** Разведчик тендеров. Ищет новые проекты по 10 источникам.

```yaml
# config/agents.yaml
scout_agent:
  role: "Старший аналитик тендеров — Таджикистан"
  goal: >
    Найти ВСЕ активные и планируемые тендеры и проекты в Таджикистане,
    которые предполагают замену или прокладку трубопроводов
    (водоснабжение, ирригация, канализация). Охватить все 10 источников.
  backstory: >
    Ты опытный аналитик закупок с 10-летним стажем работы с международными
    банками развития. Знаешь все порталы — World Bank STEP, ADB, EBRD, IsDB.
    Ищешь проекты для таджикской компании composite.tj — производителя
    стеклопластиковых труб DN 400–3000 мм.
  llm: claude-haiku-4-5-20251001
  verbose: true
  max_iter: 5
```

**Инструменты:** `DuckDuckGoSearchTool`, `WebsiteSearchTool`, `RssReaderTool`

**Источники для сканирования:**
```python
SOURCES = [
    # Приоритет 1 — международные банки
    "https://tajikistan.un.org/en/jobs",                          # UN Tajikistan
    "https://search.worldbank.org/api/v2/procnotices?format=json&project_ctry_code=TJ&rows=50",  # WB STEP API
    "https://www.adb.org/rss/projects/tenders?country=TAJ",      # ADB RSS
    "https://www.dgmarket.com/tenders/rss.do?countryId=TJ",      # DGMarket RSS
    # Приоритет 2 — исламские и евразийские фонды
    "https://www.isdb.org/project-procurement/tenders",           # IsDB
    "https://efsd.org/en/purchases/",                             # EFSD
    "https://bgate.isdb.org/CPP/EN/SearchTender.aspx",           # IsDB BGATE
    # Приоритет 3 — местные
    "https://wsip-1.tj/",                                         # WSIP-1 PMU
    "https://www.mewr.tj/",                                       # МЭВР
    "https://tenders.tj/",                                        # tenders.tj
]
```

---

## АГЕНТ 2 — DetailsAgent (src/agents/details.py)

**Роль:** Специалист по детализации. Углубляется в каждый найденный тендер.

```yaml
details_agent:
  role: "Аналитик деталей закупок"
  goal: >
    Для каждого тендера из списка Scout-агента открыть оригинальную страницу
    и извлечь: точный номер лота, бюджет, метод закупки, дату IFB,
    дату дедлайна, компонент проекта, технические спецификации труб.
  backstory: >
    Ты педантичный аналитик, который читает тендерную документацию.
    Умеешь парсить PDF, HTML-страницы и JSON ответы API.
    Никогда не пропускаешь детали — бюджет, номер гранта, дату.
  llm: claude-haiku-4-5-20251001
  verbose: true
  max_iter: 8
```

**Инструменты:** `WebsiteSearchTool`, `ScrapeWebsiteTool`, кастомный `WebScraperTool`

**Задача:**
Для каждого URL из ScoutAgent → сделать HTTP GET → распарсить:
- Номер лота/ссылки
- Бюджет ($X,XXX,XXX)
- Дата IFB / SPN / GPN
- Дедлайн подачи
- Метод закупки (NCB/ICB/RFQ)
- Компонент проекта

---

## АГЕНТ 3 — ContactAgent (src/agents/contacts.py)

**Роль:** Охотник за контактами. Находит ФИО, email, телефон, адрес ПИУ/ПМУ.

```yaml
contact_agent:
  role: "Специалист по контактам и исполнителям"
  goal: >
    Для каждого проекта найти: название ПИУ/ПМУ, ФИО директора,
    email, телефон, физический адрес. Найти подрядчика если контракт
    уже подписан. Проверить официальный сайт исполнительного агентства.
  backstory: >
    Ты нетворкер и исследователь. Знаешь, что у каждого проекта
    есть PIU (Project Implementation Unit) с публичными контактами.
    Ищешь их на сайтах ВБ, АБР, ООН и напрямую на сайтах проектов.
  llm: claude-haiku-4-5-20251001
  verbose: true
  max_iter: 5
```

**Известные контакты (включи как базовые знания):**
```python
KNOWN_CONTACTS = {
    "WSIP-1 / RWSSP (ВБ)": {
        "piu": "MIDP PMU — ЦУП MIDP",
        "director": "Саидвализода А.Р.",
        "email": "pmu@wsip-1.tj",
        "phone": "+992372331330",
        "address": "56, ул. Н. Карабаева, Душанбе",
    },
    "IsDB TJK-1013 (Хатлон)": {
        "piu": "ПИУ «DVIP»",
        "director": "Рахматзода Муродали",
        "email": "нет данных",
        "phone": "нет данных",
        "address": "10, ул. Бохтар, 3 этаж, Душанбе",
    },
    "IsDB TJK-1044 (Пяндж)": {
        "piu": "ALRI РТ",
        "director": "Давлатзода Зафарбек",
        "email": "alri.tj@mail.ru",
        "phone": "+992 37 235 76 68",
        "address": "5/1, ул. Шамси, Душанбе",
    },
    "SWIM / МЭВР (ВБ)": {
        "piu": "PIU при МЭВР РТ",
        "email": "pmu.mewr@gmail.com",
        "address": "Душанбе, ул. Шамси 5/1",
    },
    "ЕБРР Яван": {
        "piu": "ЕБРР Душанбе",
        "email": "dushanbe@ebrd.com",
        "phone": "+992 37 224 61 17",
        "address": "ул. Айни 14, 4 этаж, Душанбе",
        "portal": "https://ecepp.ebrd.com",
    },
    "ADB (53109, 50347)": {
        "piu": "ADB Tajikistan Resident Mission",
        "portal": "https://www.adb.org/countries/tajikistan/projects",
        "rss": "https://www.adb.org/rss/projects/tenders?country=TAJ",
    },
    "EFSD": {
        "portal": "https://efsd.org/en/purchases/",
        "edb": "https://eabr.org/en/projects/countries/tajikistan/",
    },
}
```

---

## АГЕНТ 4 — PipeCheckerAgent (src/agents/pipe_checker.py)

**Роль:** Технический эксперт по трубам. Фильтрует только DN ≥ 400 мм.

```yaml
pipe_checker_agent:
  role: "Технический эксперт по трубопроводным системам"
  goal: >
    Проверить каждый тендер на соответствие требованиям composite.tj:
    трубы DN ≥ 400 мм. Извлечь из документов технические параметры:
    диаметр, материал, длину, класс давления. Определить,
    может ли composite.tj (GRP/FRP трубы DN 400–3000 мм) участвовать.
  backstory: >
    Ты инженер-трубопроводчик с 15 лет опытом в водоснабжении и ирригации.
    Знаешь стандарты ISO 4427 (ПЭ), ISO 10467 (GRP), ГОСТ 18599.
    Можешь определить по описанию проекта — нужны там трубы GRP или нет.
    composite.tj производит GRP трубы DN 400–3000 мм, PN 1–32 бар,
    SN 2500–40000 Н/м².
  llm: claude-haiku-4-5-20251001
  verbose: true
```

**Логика фильтрации:**
```python
# ВКЛЮЧИТЬ если упоминается:
INCLUDE_KEYWORDS = [
    # Диаметры ≥ 400 мм
    "DN 400", "DN 500", "DN 560", "DN 600", "DN 700", "DN 800",
    "DN 900", "DN 930", "DN 1000", "DN 1200", "d=930", "d=560",
    # Типы работ
    "магистральный трубопровод", "main pipeline", "water main",
    "напорный водовод", "pressure pipeline", "коллектор",
    "ирригационный трубопровод", "irrigation pipeline",
    "канализационный коллектор", "sewer collector",
    # Общие
    "водоснабжение", "water supply", "ирригация", "irrigation",
    "мелиорация", "reclamation", "насосная станция",
]

# ИСКЛЮЧИТЬ:
EXCLUDE_KEYWORDS = [
    "газопровод", "gas pipeline", "нефтепровод", "oil pipeline",
    "электроснабжение", "power supply",
    # Маленькие диаметры (если явно указаны)
    "DN 50", "DN 63", "DN 75", "DN 90", "DN 110", "DN 160",
]

# ОЦЕНКА ПРИГОДНОСТИ для composite.tj:
# HIGH  — DN ≥ 400 мм, явно указан, водоснабжение/ирригация
# MEDIUM — ключевые слова есть, диаметр не указан явно
# LOW   — только общее упоминание воды без деталей
# NO    — малый диаметр или нерелевантный сектор
```

---

## АГЕНТ 5 — RiskAnalystAgent (src/agents/risk_analyst.py)

**Роль:** Аналитик рисков. Оценивает каждый проект по 5 критериям.

```yaml
risk_analyst_agent:
  role: "Аналитик рисков и бизнес-разведки"
  goal: >
    Оценить каждый проект по 5 критериям риска для composite.tj.
    Определить срочность (HIGH/MEDIUM/LOW). Выдать конкретные
    рекомендации — что делать и в какой срок.
  backstory: >
    Ты бизнес-аналитик, специализирующийся на рынках Центральной Азии.
    Знаешь риски: валютные (TJS нестабилен), административные
    (Таджикистан — сложная среда), технические (нестандартные диаметры).
    Умеешь оценивать конкурентную среду на донорских тендерах.
  llm: claude-haiku-4-5-20251001
  verbose: true
```

**Критерии оценки рисков:**
```python
RISK_CRITERIA = {
    "timeline":     "Срок до дедлайна: < 14 дней = HIGH, 14–60 = MEDIUM, > 60 = LOW",
    "competition":  "ICB = высокая конкуренция, NCB = средняя, RFQ = низкая",
    "diameter":     "Нестандартный DN (560, 930) = риск отсутствия сертификата",
    "procurement":  "GPN = ранняя стадия (LOW), SPN = активный тендер (HIGH)",
    "financier":    "IsDB/EFSD = правила менее знакомы, ВБ/АБР = стандартные",
}
```

---

## АГЕНТ 6 — ReportAgent (src/agents/reporter.py)

**Роль:** Генератор отчётов. Собирает финальный Excel-реестр.

```yaml
report_agent:
  role: "Старший аналитик — генерация финальных отчётов"
  goal: >
    Собрать данные от всех агентов и сгенерировать:
    1. Excel-реестр (формат таблицы composite.tj)
    2. Краткое резюме на русском (топ-3 срочных проекта)
    3. Список контактов для немедленного обращения
  backstory: >
    Ты старший аналитик с опытом подготовки отчётов для руководства.
    Умеешь структурировать данные, расставлять приоритеты, писать
    чёткие исполнительные резюме. Используешь openpyxl для Excel.
  llm: claude-sonnet-4-6   # Лучший для финального синтеза
  verbose: true
```

**Структура Excel-файла (ТОЧНО как в реестре composite.tj):**
```python
EXCEL_COLUMNS = [
    ("A", "№",                         5),
    ("B", "Название проекта",          50),   # merged B+C
    ("C", "",                          0),    # merged с B
    ("D", "Исполнительное агентство",  28),
    ("E", "Финансирующее учреждение",  28),
    ("F", "Статус проекта",            20),
    ("G", "Срок реализации проекта",   18),
    ("H", "Продолжительность (мес.)",  12),
    ("I", "Компании-исполнители",      30),
    ("J", "Бюджет (доля Барса) USD",   30),
    ("K", "Проблемы / Риски",          35),
    ("L", "Ответственный / Контакты",  38),
]

# Дополнительные колонки (новые, добавить после L):
EXTRA_COLUMNS = [
    ("M", "Диаметр труб (DN, мм)",     15),
    ("N", "Материал труб",             15),
    ("O", "Длина (км)",                10),
    ("P", "Метод закупки",             15),
    ("Q", "Дата IFB/GPN",              15),
    ("R", "Дедлайн тендера",           15),
    ("S", "Пригодность для Барса",     18),  # HIGH/MEDIUM/LOW/NO
    ("T", "Ссылка на тендер",          45),
]
```

**Цветовая кодировка строк по статусу:**
```python
STATUS_COLORS = {
    "Активен":            "D4EDDA",   # зелёный
    "В исполнении":       "D4EDDA",   # зелёный
    "Не объявлен":        "D0E8FF",   # синий  ← ГЛАВНАЯ ВОЗМОЖНОСТЬ
    "Ожидает":            "FFF3CD",   # жёлтый
    "Подготовка":         "FFE4CC",   # оранжевый
    "Новый — GPN":        "FFE4CC",   # оранжевый
}

URGENCY_COLORS = {
    "HIGH":   "F8D7DA",  # красный фон
    "MEDIUM": "FFF3CD",  # жёлтый фон
    "LOW":    "FFFFFF",  # белый
}
```

---

## СБОРКА CREW (src/crew.py)

```python
from crewai import Crew, Process, Agent, Task

class TajikistanPipeMonitor:
    """
    CrewAI система мониторинга тендеров по трубопроводам в Таджикистане.
    Процесс: hierarchical (менеджер координирует всех агентов).
    """

    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.scout_agent(),
                self.details_agent(),
                self.contact_agent(),
                self.pipe_checker_agent(),
                self.risk_analyst_agent(),
                self.report_agent(),
            ],
            tasks=[
                self.scout_task(),       # 1. Поиск тендеров
                self.details_task(),     # 2. Детализация каждого
                self.contact_task(),     # 3. Контакты
                self.pipe_task(),        # 4. Фильтр DN ≥ 400 мм
                self.risk_task(),        # 5. Оценка рисков
                self.report_task(),      # 6. Финальный Excel
            ],
            process=Process.hierarchical,
            manager_agent=self.manager_agent(),
            verbose=True,
            memory=True,              # агенты помнят контекст
            max_rpm=10,               # не перегружать API
            output_log_file="output/crew_log.txt",
        )

    def manager_agent(self) -> Agent:
        """Менеджер-координатор всего процесса."""
        return Agent(
            role="Координатор проекта мониторинга тендеров",
            goal=(
                "Координировать работу всех 6 агентов, обеспечивать "
                "последовательную передачу данных и качество результатов."
            ),
            backstory=(
                "Ты опытный руководитель проектов. Следишь за тем, чтобы "
                "каждый агент выполнил свою задачу и передал результат "
                "следующему. Контролируешь качество и полноту данных."
            ),
            llm="claude-haiku-4-5-20251001",
            verbose=True,
            allow_delegation=True,
        )
```

---

## ЗАДАЧИ (Tasks)

### Task 1 — ScoutTask
```yaml
scout_task:
  description: >
    Просканируй следующие 10 источников на предмет тендеров и проектов
    по водоснабжению, ирригации и канализации в Таджикистане:

    1. UN Tajikistan (tajikistan.un.org/en/jobs)
    2. World Bank STEP API (search.worldbank.org/api/v2/procnotices?project_ctry_code=TJ)
    3. ADB RSS (adb.org/rss/projects/tenders?country=TAJ)
    4. DGMarket RSS (dgmarket.com/tenders/rss.do?countryId=TJ)
    5. IsDB BGATE (bgate.isdb.org/CPP/EN/SearchTender.aspx?country=TJ)
    6. IsDB проекты (isdb.org/project-procurement/tenders)
    7. EFSD (efsd.org/en/purchases)
    8. WSIP-1 PMU (wsip-1.tj)
    9. МЭВР (mewr.tj)
    10. tenders.tj

    Ключевые слова поиска: water supply, irrigation, pipeline, pipe,
    водоснабжение, ирригация, трубопровод, труба, водовод, мелиорация,
    канализация, коллектор.

    Для каждого найденного тендера верни: название, URL, донор, дата.
    Минимум 10 результатов. Если источник недоступен — логируй и продолжай.

  expected_output: >
    JSON-список тендеров. Каждый элемент:
    {"title": str, "url": str, "donor": str, "date": str, "source": str}
    Минимум 10 записей. Только Таджикистан. Только вода/ирригация/трубы.

  agent: scout_agent
```

### Task 2 — DetailsTask
```yaml
details_task:
  description: >
    Для каждого тендера из списка Scout-агента перейди на страницу
    и извлеки полные детали. Используй HTTP GET + BeautifulSoup.

    Для каждого тендера извлечь:
    - Полное название контракта
    - Номер лота/ссылки (WSIP-W-PMU/001 и т.д.)
    - Номер проекта ВБ/АБР/IsDB
    - Номер гранта/кредита
    - Общий бюджет ($XXX,XXX)
    - Дата публикации IFB
    - Дедлайн подачи предложений
    - Метод закупки (NCB/ICB/RFQ/GPN)
    - Компонент проекта
    - Технические параметры если указаны (длина, диаметр, тип труб)

    Если данные недоступны — указывай "нет данных".

  expected_output: >
    Обогащённый JSON-список с полными деталями каждого тендера.
    Все поля модели Tender кроме contacts и pipe_analysis.

  context: [scout_task]
  agent: details_agent
```

### Task 3 — ContactTask
```yaml
contact_task:
  description: >
    Для каждого проекта из списка DetailsAgent найди контактные данные:

    1. Название ПИУ/ПМУ
    2. ФИО директора/ответственного
    3. Email
    4. Телефон
    5. Адрес офиса
    6. Если контракт подписан — найди название компании-подрядчика

    Используй официальные сайты проектов, tajikistan.un.org,
    portals ВБ/АБР/IsDB. Используй базу известных контактов из
    конфига (KNOWN_CONTACTS).

    Для незнакомых проектов ищи через DuckDuckGoSearchTool:
    "[название проекта] PIU director email Tajikistan"

  expected_output: >
    JSON с контактами для каждого проекта.
    {"project_id": ..., "piu": ..., "director": ...,
     "email": ..., "phone": ..., "address": ..., "contractor": ...}

  context: [scout_task, details_task]
  agent: contact_agent
```

### Task 4 — PipeTask
```yaml
pipe_task:
  description: >
    Проверь каждый тендер на соответствие требованиям composite.tj.
    composite.tj производит стеклопластиковые (GRP/FRP) трубы DN 400–3000 мм.

    Для каждого тендера:
    1. Ищи упоминания диаметра труб (DN, d=, мм, mm)
    2. Если DN ≥ 400 мм → dn_400_confirmed = True
    3. Если DN < 400 мм → dn_400_confirmed = False (исключить)
    4. Если диаметр не указан → dn_400_confirmed = None (уточнить)
    5. Определи материал труб: ПЭ / ПВХ / сталь / ВЧШГ / GRP / не указан
    6. Определи пригодность: HIGH / MEDIUM / LOW / NO

    Пригодность HIGH если:
    - DN ≥ 400 мм явно указан
    - Магистральный водопровод или ирригационный коллектор
    - Бюджет > $3 млн

    Пригодность MEDIUM если:
    - Водоснабжение или ирригация без явного указания диаметра
    - Бюджет $500K–$3 млн

    Пригодность LOW если:
    - Только общее упоминание воды
    - Малый масштаб

    Пригодность NO если:
    - DN < 400 мм явно указан
    - Нерелевантный сектор (газ, нефть, электро)

  expected_output: >
    JSON список с полями: project_id, pipe_diameter_mm, pipe_material,
    pipe_length_km, dn_400_confirmed, suitability (HIGH/MEDIUM/LOW/NO),
    technical_notes (строка с обоснованием)

  context: [scout_task, details_task]
  agent: pipe_checker_agent
```

### Task 5 — RiskTask
```yaml
risk_task:
  description: >
    Оцени каждый проект по 5 критериям риска для composite.tj:

    1. ВРЕМЕННОЙ РИСК:
       - Дедлайн < 14 дней → HIGH (действовать сейчас)
       - Дедлайн 14–60 дней → MEDIUM
       - Дедлайн > 60 дней или не указан → LOW

    2. КОНКУРЕНТНЫЙ РИСК:
       - ICB (International) → высокая конкуренция
       - NCB (National) → средняя
       - RFQ / Direct → низкая

    3. ТЕХНИЧЕСКИЙ РИСК:
       - Нестандартный диаметр (DN 560, 930) → нужен сертификат
       - GRP трубы не указаны явно → риск непринятия
       - Нет ТЗ в открытом доступе → неопределённость

    4. АДМИНИСТРАТИВНЫЙ РИСК:
       - Новый донор (EFSD, IsDB) → незнакомые правила
       - Нет публичного контракта → сложность субподряда
       - Тендер отменён/повторный → нестабильность

    5. ФИНАНСОВЫЙ РИСК:
       - Бюджет < $1 млн → низкий приоритет
       - Доля Барса неизвестна → расчёт приблизительный
       - Оплата в TJS → курсовой риск

    Для каждого проекта: итоговая срочность (HIGH/MEDIUM/LOW)
    + конкретные рекомендации (что делать, кому писать, в какой срок).

  expected_output: >
    JSON список: {project_id, urgency, risk_score (1-10),
    risk_details, recommendations, action_deadline}

  context: [scout_task, details_task, contact_task, pipe_task]
  agent: risk_analyst_agent
```

### Task 6 — ReportTask
```yaml
report_task:
  description: >
    Собери данные от всех агентов и создай финальный отчёт.

    СОЗДАЙ 3 файла в папке output/:

    1. output/tajikistan_pipe_registry_YYYYMMDD.xlsx
       - Точная структура реестра composite.tj (13 колонок + 6 новых)
       - Все проекты с заполненными полями
       - Цветовая кодировка по статусу и срочности
       - Заморозка заголовка (freeze_panes)
       - Строка с источниками и датой внизу
       - Подходит для прямой загрузки в Excel composite.tj

    2. output/urgent_summary_YYYYMMDD.txt
       Текстовое резюме на русском языке:
       - Топ-3 СРОЧНЫХ проекта (что делать сегодня)
       - Топ-3 СТРАТЕГИЧЕСКИХ проекта (готовиться сейчас)
       - Список email для рассылки запросов
       - Следующие шаги с конкретными датами

    3. output/contacts_YYYYMMDD.json
       Структурированная контактная книга всех ПИУ/ПМУ.

    ТРЕБОВАНИЯ К EXCEL:
    - Заголовок строки 1: "РЕЕСТР ПРОЕКТОВ" (merged A1:T1)
    - Строка 2: "ТЕКУЩИЕ ПРОЕКТЫ НА СТАДИИ РЕАЛИЗАЦИИ" (merged)
    - Строки 3-4: заголовки колонок
    - Строки с 5: данные проектов
    - Ширина колонок: точно по EXCEL_COLUMNS из конфига
    - Merge B+C для названия проекта в каждой строке
    - Wrap text во всех ячейках данных
    - Высота строк данных: 90 pt
    - Font: Arial 9pt для данных, Arial 10pt bold для заголовков

  expected_output: >
    Подтверждение создания 3 файлов с путями.
    Краткое резюме: сколько проектов найдено, топ-3 срочных,
    общий потенциальный бюджет на трубы.

  context: [scout_task, details_task, contact_task, pipe_task, risk_task]
  agent: report_agent
  output_file: "output/tajikistan_pipe_registry_latest.xlsx"
```

---

## КАСТОМНЫЕ ИНСТРУМЕНТЫ (src/tools/)

### WebScraperTool (src/tools/web_scraper.py)
```python
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
```

### RssReaderTool (src/tools/rss_reader.py)
```python
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
```

### ExcelWriterTool (src/tools/excel_writer.py)
```python
from crewai.tools import BaseTool
import json, openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from datetime import datetime

class ExcelWriterTool(BaseTool):
    name: str = "Excel Registry Writer"
    description: str = (
        "Создаёт Excel-реестр проектов в формате composite.tj. "
        "Параметр: projects_json (JSON-строка со списком проектов). "
        "Сохраняет файл в output/. Возвращает путь к файлу."
    )

    def _run(self, projects_json: str) -> str:
        # Реализация создания Excel — полный код генерации
        # с заголовками, стилями, merge cells, цветами статусов
        # ... (полный код по аналогии с fill_registry.py)
        pass
```

---

## ТОЧКА ВХОДА (main.py)

```python
#!/usr/bin/env python3
"""
Tajikistan Pipe Monitor — CrewAI агенты для поиска тендеров по трубам.
Запуск: python main.py
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from src.crew import TajikistanPipeMonitor

load_dotenv()

def main():
    print("=" * 60)
    print("TAJIKISTAN PIPE TENDER MONITOR — composite.tj")
    print(f"Запуск: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Входные данные для агентов
    inputs = {
        "search_date": datetime.now().strftime("%Y-%m-%d"),
        "company": "composite.tj",
        "product": "GRP/FRP трубы DN 400–3000 мм",
        "target_country": "Таджикистан",
        "min_pipe_diameter": 400,
        "output_dir": "output",
    }

    result = TajikistanPipeMonitor().crew().kickoff(inputs=inputs)

    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ:")
    print(result)
    print("=" * 60)
    print(f"\nФайлы сохранены в папке output/")

if __name__ == "__main__":
    main()
```

---

## .env.example

```env
# LLM — Anthropic (Claude)
ANTHROPIC_API_KEY=your_anthropic_key_here

# LLM — Google (Gemini) — альтернативный бэкенд
GEMINI_API_KEY=your_gemini_key_here

# Настройки
MIN_PIPE_DIAMETER_MM=400
TARGET_COUNTRY=Tajikistan
OUTPUT_DIR=output
LOG_LEVEL=INFO

# composite.tj + Барс
COMPANY_NAME=composite.tj
CONTRACTOR_NAME=Барс
PRODUCTS=GRP pipes DN 400-3000mm
```

---

## ПРАВИЛА НАПИСАНИЯ КОДА

1. **LLM:** Все агенты используют `claude-haiku-4-5-20251001` кроме ReportAgent
   (`claude-sonnet-4-6`). Альтернатива: `gemini/gemini-2.5-flash` через litellm.
   Это критично для экономии токенов.

2. **Поиск:** Использовать `DuckDuckGoSearchTool` (без API-ключа).
   НЕ использовать SerperDevTool.

3. **Парсинг:** Никогда не используй BeautifulSoup на JS-сайтах. Для ADB, EBRD,
   World Bank STEP — только JSON API или RSS. Для HTML — только статичные страницы.
   Все HTTP-запросы — с retry, таймаутами и ротацией User-Agent.

4. **Pydantic модель Tender обязательна** для передачи данных между агентами.
   Используй `output_pydantic=Tender` или `output_json=Tender` в задачах.

5. **Контекст задач** (`context=[...]`) должен быть правильно выстроен по цепочке.
   ReportTask получает контекст от всех 5 предыдущих задач.

6. **Excel-файл** должен точно соответствовать структуре оригинального реестра
   composite.tj (колонки A–L совпадают с оригиналом, M–T — новые).

7. **Обработка ошибок:** если источник недоступен — логировать и продолжать,
   не падать. Использовать `try/except` во всех инструментах.

8. **Файлы output** именовать с датой: `tajikistan_pipe_registry_20260527.xlsx`

9. **Барс и composite.tj:** Барс — подрядчик (участвует в тендерах),
   composite.tj — поставщик труб GRP DN 400–3000 мм.
   В колонках Excel «доля Барса» = доля подрядного контракта.

---

## ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

После запуска `python main.py` в папке `output/` должны появиться:

```
output/
├── tajikistan_pipe_registry_20260527.xlsx   ← ГЛАВНЫЙ ФАЙЛ
│   Структура: заголовок + 13+ строк проектов
│   Колонки: №, Название, Агентство, Финансирующий, Статус,
│             Срок, Продолж., Подрядчик, Бюджет/Барс, Риски,
│             Контакты, DN, Материал, Длина, Метод, IFB,
│             Дедлайн, Пригодность, Ссылка
│
├── urgent_summary_20260527.txt              ← РЕЗЮМЕ
│   Топ-3 срочных + топ-3 стратегических + чеклист
│
└── contacts_20260527.json                   ← КОНТАКТЫ
    ПИУ/ПМУ всех проектов + email + телефон
```
