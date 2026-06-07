#!/usr/bin/env python3
"""
Tajikistan Pipe Monitor — CrewAI агенты для поиска тендеров по трубам.
Запуск: python main.py

Оптимизировано:
  - Параллельный Python-фетчер собирает все 10 источников за ~8–12 с (без LLM)
  - Agents получают готовые кандидаты → меньше итераций и токенов
  - Process.sequential (нет менеджера) → нет лишних LLM-вызовов
"""
import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.parallel_fetcher import fetch_all_sources, format_for_prompt
from src.crew import TajikistanPipeMonitor


def main():
    print("=" * 60)
    print("TAJIKISTAN PIPE TENDER MONITOR — composite.tj")
    print(f"Запуск: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    company      = os.getenv("COMPANY_NAME", "composite.tj")
    contractor   = os.getenv("CONTRACTOR_NAME", "Барс")
    products     = os.getenv("PRODUCTS", "GRP/FRP трубы DN 400–3000 мм")
    target       = os.getenv("TARGET_COUNTRY", "Таджикистан")
    min_diameter = int(os.getenv("MIN_PIPE_DIAMETER_MM", "400"))
    output_dir   = os.getenv("OUTPUT_DIR", "output")
    max_results  = int(os.getenv("MAX_RESULTS", "15"))
    max_cands    = int(os.getenv("MAX_CANDIDATES", str(max(max_results * 3, 10))))

    print(f"\n📋 Компания:    {company}")
    print(f"🏗️  Подрядчик:   {contractor}")
    print(f"🔧 Продукция:   {products}")
    print(f"🌍 Страна:      {target}")
    print(f"📏 Мин. диаметр: DN {min_diameter} мм\n")

    # ── Шаг 1: параллельный Python-фетчинг (без LLM) ─────────────────────────
    print("🔍 Предзагрузка источников (параллельно)...")
    t0 = time.monotonic()
    candidates = fetch_all_sources(max_candidates=max_cands)
    fetch_time = time.monotonic() - t0
    print(f"   Найдено кандидатов: {len(candidates)} за {fetch_time:.1f} с\n")

    # Форматируем в текст (без фигурных скобок — безопасно для CrewAI format())
    candidates_text = format_for_prompt(candidates)

    # ── Шаг 2: запуск CrewAI агентов ─────────────────────────────────────────
    inputs = {
        "search_date":       datetime.now().strftime("%Y-%m-%d"),
        "company":           company,
        "contractor":        contractor,
        "product":           products,
        "target_country":    target,
        "min_pipe_diameter": min_diameter,
        "output_dir":        output_dir,
        "candidates_text":   candidates_text,
        "max_results":       str(max_results),
    }

    try:
        t1 = time.monotonic()
        result = TajikistanPipeMonitor().crew().kickoff(inputs=inputs)
        agent_time = time.monotonic() - t1

        print("\n" + "=" * 60)
        print("✅ РЕЗУЛЬТАТ:")
        print(result)
        print("=" * 60)
        print(f"\n📁 Файлы: {output_dir}/")
        print(f"⏱️  Фетчинг: {fetch_time:.0f}с | Агенты: {agent_time:.0f}с | Итого: {fetch_time + agent_time:.0f}с")

    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ Ошибка: {str(e)}", file=sys.stderr)
        logging.getLogger(__name__).exception("Подробности:")
        sys.exit(1)


if __name__ == "__main__":
    main()
