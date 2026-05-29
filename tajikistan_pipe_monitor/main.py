#!/usr/bin/env python3
"""
Tajikistan Pipe Monitor — CrewAI агенты для поиска тендеров по трубам.
Запуск: python main.py
"""
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables BEFORE any other imports that might need them
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Add current directory to path to ensure src can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.crew import TajikistanPipeMonitor


def main():
    print("=" * 60)
    print("TAJIKISTAN PIPE TENDER MONITOR — composite.tj")
    print(f"Запуск: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Read settings from .env with sensible defaults
    company = os.getenv("COMPANY_NAME", "composite.tj")
    contractor = os.getenv("CONTRACTOR_NAME", "")
    products = os.getenv("PRODUCTS", "Трубы любых видов от 400мм")
    target_country = os.getenv("TARGET_COUNTRY", "Таджикистан")
    min_diameter = int(os.getenv("MIN_PIPE_DIAMETER_MM", "400"))
    output_dir = os.getenv("OUTPUT_DIR", "output")

    # Входные данные для агентов
    inputs = {
        "search_date": datetime.now().strftime("%Y-%m-%d"),
        "company": company,
        "contractor": contractor,
        "product": products,
        "target_country": target_country,
        "min_pipe_diameter": min_diameter,
        "output_dir": output_dir,
    }

    print(f"\n📋 Компания: {company}")
    if contractor:
        print(f"🏗️  Подрядчик: {contractor}")
    print(f"🔧 Продукция: {products}")
    print(f"🌍 Страна: {target_country}")
    print(f"📏 Мин. диаметр: DN {min_diameter} мм")
    print(f"📂 Папка вывода: {output_dir}/\n")

    try:
        result = TajikistanPipeMonitor().crew().kickoff(inputs=inputs)

        print("\n" + "=" * 60)
        print("✅ РЕЗУЛЬТАТ:")
        print(result)
        print("=" * 60)
        print(f"\n📁 Файлы сохранены в папке {output_dir}/")
    except SystemExit:
        raise  # Don't catch intentional exits from crew.py
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении: {str(e)}", file=sys.stderr)
        logging.getLogger(__name__).exception("Подробности ошибки:")
        sys.exit(1)

if __name__ == "__main__":
    main()
