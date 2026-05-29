import os
import yaml
from crewai import Agent, LLM
from src.tools import DuckDuckGoSearchTool, RssReaderTool, WebScraperTool

SOURCES = [
    "https://tajikistan.un.org/en/jobs",
    "https://search.worldbank.org/api/v2/procnotices?format=json&project_ctry_code=TJ&rows=50",
    "https://www.adb.org/rss/projects/tenders?country=TAJ",
    "https://www.dgmarket.com/tenders/rss.do?countryId=TJ",
    "https://www.isdb.org/project-procurement/tenders",
    "https://efsd.org/en/purchases/",
    "https://bgate.isdb.org/CPP/EN/SearchTender.aspx",
    "https://wsip-1.tj/",
    "https://www.mewr.tj/",
    "https://tenders.tj/",
]

def create_scout_agent(llm: LLM) -> Agent:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config",
        "agents.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)["scout_agent"]
        
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        verbose=config.get("verbose", True),
        max_iter=config.get("max_iter", 5),
        llm=llm,
        tools=[
            DuckDuckGoSearchTool(),
            RssReaderTool(),
            WebScraperTool(),
        ],
    )
