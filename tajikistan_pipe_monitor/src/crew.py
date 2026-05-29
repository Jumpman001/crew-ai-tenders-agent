import os
import sys
import logging
from crewai import Crew, Process, Agent, LLM
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
    CrewAI система мониторинга тендеров по трубопроводам в Таджикистане.
    Процесс: hierarchical (менеджер координирует всех агентов).
    """
    
    def __init__(self):
        self._setup_llms()

    def _setup_llms(self):
        cerebras_key = os.environ.get("CEREBRAS_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
        
        has_cerebras = cerebras_key and "your_" not in cerebras_key
        has_anthropic = anthropic_key and "your_" not in anthropic_key
        has_gemini = gemini_key and "your_" not in gemini_key
        has_openrouter = openrouter_key and "your_" not in openrouter_key
        
        # Determine provider: user can force via LLM_PROVIDER env var.
        # Auto-detect: prefer OpenRouter, then Cerebras, then Gemini, then Anthropic.
        provider = os.environ.get("LLM_PROVIDER", "").lower()
        if not provider:
            if has_openrouter:
                provider = "openrouter"
            elif has_cerebras:
                provider = "cerebras"
            elif has_gemini:
                provider = "gemini"
            elif has_anthropic:
                provider = "anthropic"
            else:
                print(
                    "\n⚠️  НИ ОДИН API-КЛЮЧ НЕ НАЙДЕН!\n"
                    "   Укажите OPENROUTER_API_KEY, CEREBRAS_API_KEY, GEMINI_API_KEY или ANTHROPIC_API_KEY в файле .env\n"
                    "   Подробнее: .env.example\n",
                    file=sys.stderr,
                )
                raise SystemExit(1)

        self._provider = provider

        if provider == "openrouter":
            if not has_openrouter:
                print(
                    "\n⚠️  LLM_PROVIDER=openrouter, но OPENROUTER_API_KEY не задан в .env!\n",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            logger.info("Используется бэкенд: OpenRouter")
            print("🤖 LLM бэкенд: OpenRouter (qwen3-coder:free)")
            self.llm_fast = LLM(model="openrouter/qwen/qwen3-coder:free", api_key=openrouter_key)
            self.llm_smart = LLM(model="openrouter/qwen/qwen3-coder:free", api_key=openrouter_key)
            self.llm_manager = LLM(model="openrouter/qwen/qwen3-coder:free", api_key=openrouter_key)
        elif provider == "deepseek":
            deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not deepseek_key:
                logger.error("DEEPSEEK_API_KEY не установлен!")
                raise SystemExit(1)
            logger.info("Используется бэкенд: DeepSeek")
            print("🤖 LLM бэкенд: DeepSeek (deepseek-chat)")
            self.llm_fast = LLM(
                model="deepseek/deepseek-chat", 
                api_key=deepseek_key
            )
            self.llm_smart = LLM(
                model="deepseek/deepseek-chat", 
                api_key=deepseek_key
            )
            self.llm_manager = LLM(
                model="deepseek/deepseek-chat", 
                api_key=deepseek_key
            )
        elif provider == "cerebras":
            if not has_cerebras:
                print(
                    "\n⚠️  LLM_PROVIDER=cerebras, но CEREBRAS_API_KEY не задан в .env!\n",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            logger.info("Используется бэкенд: Cerebras")
            print("🤖 LLM бэкенд: Cerebras (gpt-oss-120b)")
            os.environ["CEREBRAS_API_KEY"] = cerebras_key
            cerebras_kwargs = dict(
                model="openai/gpt-oss-120b",
                base_url="https://api.cerebras.ai/v1",
                api_key=cerebras_key,
            )
            self.llm_fast = LLM(**cerebras_kwargs)
            self.llm_smart = LLM(**cerebras_kwargs)
            self.llm_manager = LLM(**cerebras_kwargs)
        elif provider == "gemini":
            if not has_gemini:
                print(
                    "\n⚠️  LLM_PROVIDER=gemini, но GEMINI_API_KEY не задан в .env!\n",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            logger.info("Используется бэкенд: Google Gemini")
            print("🤖 LLM бэкенд: Google Gemini (gemini-2.0-flash)")
            self.llm_fast = LLM(model="gemini/gemini-2.0-flash", api_key=gemini_key)
            self.llm_smart = LLM(model="gemini/gemini-2.0-flash", api_key=gemini_key)
            self.llm_manager = LLM(model="gemini/gemini-2.0-flash", api_key=gemini_key)
        else:
            if not has_anthropic:
                print(
                    "\n⚠️  LLM_PROVIDER=anthropic, но ANTHROPIC_API_KEY не задан в .env!\n",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            logger.info("Используется бэкенд: Anthropic Claude")
            print("🤖 LLM бэкенд: Anthropic Claude (haiku / sonnet)")
            self.llm_fast = LLM(model="anthropic/claude-haiku-4-5-20251001", api_key=anthropic_key)
            self.llm_smart = LLM(model="anthropic/claude-sonnet-4-6-20250514", api_key=anthropic_key)
            self.llm_manager = LLM(model="anthropic/claude-haiku-4-5-20251001", api_key=anthropic_key)

    def _get_embedder_config(self):
        """Возвращает конфигурацию embedder для memory, или None если недоступно."""
        if self._provider == "gemini":
            gemini_key = os.environ.get("GEMINI_API_KEY", "")
            return {
                "provider": "google-generativeai",
                "config": {
                    "model": "models/text-embedding-004",
                    "api_key": gemini_key,
                },
            }
        # Cerebras и Anthropic не имеют embedding API — отключаем memory
        return None

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
            llm=self.llm_manager,
            verbose=True,
            allow_delegation=True,
        )

    def crew(self) -> Crew:
        # Create agents
        scout = create_scout_agent(self.llm_fast)
        details = create_details_agent(self.llm_fast)
        contacts = create_contact_agent(self.llm_fast)
        pipe_checker = create_pipe_checker_agent(self.llm_fast)
        risk_analyst = create_risk_analyst_agent(self.llm_fast)
        reporter = create_reporter_agent(self.llm_smart)

        # Create tasks with dependency contexts
        task_scout = create_scout_task(scout)
        task_details = create_details_task(details, context=[task_scout])
        task_contacts = create_contact_task(contacts, context=[task_scout, task_details])
        task_pipe = create_pipe_task(pipe_checker, context=[task_scout, task_details])
        
        # Risk analysis takes context from everything before it
        task_risk = create_risk_task(risk_analyst, context=[task_scout, task_details, task_contacts, task_pipe])
        
        # Report compiles everything
        task_report = create_report_task(reporter, context=[task_scout, task_details, task_contacts, task_pipe, task_risk])

        # Memory: отключена (Cerebras не имеет embedding API)
        embedder_config = self._get_embedder_config()
        use_memory = embedder_config is not None
        if not use_memory:
            print("ℹ️  Memory отключена (embedding провайдер недоступен)")

        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)

        # Cerebras имеет высокие лимиты RPM, Gemini free tier — низкие
        rpm_limit = 30 if self._provider == "cerebras" else 4

        crew_kwargs = dict(
            agents=[scout, details, contacts, pipe_checker, risk_analyst, reporter],
            tasks=[task_scout, task_details, task_contacts, task_pipe, task_risk, task_report],
            process=Process.hierarchical,
            manager_agent=self.manager_agent(),
            verbose=True,
            memory=use_memory,
            max_rpm=rpm_limit,
            output_log_file="output/crew_log.txt",
        )

        if embedder_config:
            crew_kwargs["embedder"] = embedder_config

        return Crew(**crew_kwargs)

