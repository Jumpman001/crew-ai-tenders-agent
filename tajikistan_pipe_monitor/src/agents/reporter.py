import os
import yaml
from crewai import Agent, LLM
from src.tools.excel_writer import ExcelWriterTool

def create_reporter_agent(llm: LLM) -> Agent:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config",
        "agents.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)["report_agent"]
        
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        verbose=config.get("verbose", True),
        llm=llm,
        tools=[
            ExcelWriterTool(),
        ],
    )
