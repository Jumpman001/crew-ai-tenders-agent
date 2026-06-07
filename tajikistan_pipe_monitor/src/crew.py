import os
import sys
import logging
from crewai import Crew, Process, LLM
from src.agents import (
    create_scout_agent,
    create_details_agent,
    create_contact_agent,
    create_pipe_checker_agent,
    create_risk_analyst_agent,
    create_reporter_agent,
)
from src.tasks import (
    create_scout_task,
    create_details_task,
    create_contact_task,
    create_pipe_task,
    create_risk_task,
    create_report_task,
)

logger = logging.getLogger(__name__)


class TajikistanPipeMonitor:
    """
    CrewAI система мониторинга тендеров.
    Process.sequential — без менеджера, минимум накладных LLM-вызовов.
    Источники предзагружаются параллельно в Python ещё до запуска crew.
    """

    def __init__(self):
        self._setup_llms()

    def _setup_llms(self):
        anthropic_key  = os.environ.get("ANTHROPIC_API_KEY", "")
        gemini_key     = os.environ.get("GEMINI_API_KEY", "")
        openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
        cerebras_key   = os.environ.get("CEREBRAS_API_KEY", "")
        deepseek_key   = os.environ.get("DEEPSEEK_API_KEY", "")

        def _valid(k: str) -> bool:
            return bool(k) and "your_" not in k

        provider = os.environ.get("LLM_PROVIDER", "").lower()
        if not provider:
            if _valid(openrouter_key):
                provider = "openrouter"
            elif _valid(cerebras_key):
                provider = "cerebras"
            elif _valid(gemini_key):
                provider = "gemini"
            elif _valid(anthropic_key):
                provider = "anthropic"
            elif _valid(deepseek_key):
                provider = "deepseek"
            else:
                print(
                    "\n⚠️  НИ ОДИН API-КЛЮЧ НЕ НАЙДЕН!\n"
                    "   Укажите OPENROUTER_API_KEY, CEREBRAS_API_KEY, GEMINI_API_KEY,\n"
                    "   ANTHROPIC_API_KEY или DEEPSEEK_API_KEY в файле .env\n"
                    "   Или запустите локально: LLM_PROVIDER=ollama\n",
                    file=sys.stderr,
                )
                raise SystemExit(1)

        self._provider = provider
        self.llm_fast, self.llm_smart = self._build_llms(
            provider, anthropic_key, gemini_key, openrouter_key, cerebras_key, deepseek_key
        )

    def _build_llms(self, provider, anthropic_key, gemini_key, openrouter_key, cerebras_key, deepseek_key):
        if provider == "ollama":
            model = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
            base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            print(f"🤖 LLM: Ollama локальная модель ({model})")
            m = LLM(model=f"ollama/{model}", base_url=base_url)
            return m, m

        if provider == "openrouter":
            print("🤖 LLM: OpenRouter (qwen3-coder:free)")
            m = LLM(model="openrouter/qwen/qwen3-coder:free", api_key=openrouter_key)
            return m, m

        if provider == "cerebras":
            print("🤖 LLM: Cerebras (gpt-oss-120b)")
            m = LLM(model="openai/gpt-oss-120b", base_url="https://api.cerebras.ai/v1", api_key=cerebras_key)
            return m, m

        if provider == "deepseek":
            print("🤖 LLM: DeepSeek (deepseek-chat)")
            m = LLM(model="deepseek/deepseek-chat", api_key=deepseek_key)
            return m, m

        if provider == "gemini":
            print("🤖 LLM: Gemini (gemini-2.0-flash)")
            m = LLM(model="gemini/gemini-2.0-flash", api_key=gemini_key)
            return m, m

        # anthropic
        print("🤖 LLM: Anthropic (haiku fast / sonnet smart)")
        fast  = LLM(model="anthropic/claude-haiku-4-5-20251001",       api_key=anthropic_key)
        smart = LLM(model="anthropic/claude-sonnet-4-6-20250514", api_key=anthropic_key)
        return fast, smart

    def crew(self) -> Crew:
        # Agents
        scout        = create_scout_agent(self.llm_fast)
        details      = create_details_agent(self.llm_fast)
        contacts     = create_contact_agent(self.llm_fast)
        pipe_checker = create_pipe_checker_agent(self.llm_fast)
        risk_analyst = create_risk_analyst_agent(self.llm_fast)
        reporter     = create_reporter_agent(self.llm_smart)

        # Tasks — контекст только там, где действительно нужен
        task_scout   = create_scout_task(scout)
        task_details = create_details_task(details, context=[task_scout])
        task_contacts = create_contact_task(contacts, context=[task_details])
        task_pipe    = create_pipe_task(pipe_checker, context=[task_details])
        task_risk    = create_risk_task(risk_analyst, context=[task_details, task_pipe])

        # ReportTask получает только 3 задачи вместо 5 — меньше контекста
        task_report = create_report_task(
            reporter,
            context=[task_details, task_contacts, task_pipe, task_risk],
        )

        os.makedirs("output", exist_ok=True)

        # Gemini free tier — 15 RPM (было 4), остальные — 30
        rpm = 15 if self._provider == "gemini" else 30

        return Crew(
            agents=[scout, details, contacts, pipe_checker, risk_analyst, reporter],
            tasks=[task_scout, task_details, task_contacts, task_pipe, task_risk, task_report],
            process=Process.sequential,   # без менеджера — нет лишних LLM-вызовов
            verbose=False,
            memory=False,                 # embedding не нужен — экономия токенов
            max_rpm=rpm,
            output_log_file="output/crew_log.txt",
        )
