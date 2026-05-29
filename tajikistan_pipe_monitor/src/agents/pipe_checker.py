import os
import yaml
from crewai import Agent, LLM

INCLUDE_KEYWORDS = [
    "DN 400", "DN 500", "DN 560", "DN 600", "DN 700", "DN 800",
    "DN 900", "DN 930", "DN 1000", "DN 1200", "d=930", "d=560",
    "магистральный трубопровод", "main pipeline", "water main",
    "напорный водовод", "pressure pipeline", "коллектор",
    "ирригационный трубопровод", "irrigation pipeline",
    "канализационный коллектор", "sewer collector",
    "водоснабжение", "water supply", "ирригация", "irrigation",
    "мелиорация", "reclamation", "насосная станция",
]

EXCLUDE_KEYWORDS = [
    "газопровод", "gas pipeline", "нефтепровод", "oil pipeline",
    "электроснабжение", "power supply",
    "DN 50", "DN 63", "DN 75", "DN 90", "DN 110", "DN 160",
]

def create_pipe_checker_agent(llm: LLM) -> Agent:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config",
        "agents.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)["pipe_checker_agent"]
        
    backstory = config["backstory"] + f"\n\nПравила фильтрации:\nКлючевые слова для включения: {', '.join(INCLUDE_KEYWORDS)}\nКлючевые слова для исключения: {', '.join(EXCLUDE_KEYWORDS)}"
        
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=backstory,
        verbose=config.get("verbose", True),
        llm=llm,
        tools=[],
    )
