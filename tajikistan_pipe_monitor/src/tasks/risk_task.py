import os
import yaml
from typing import List
from crewai import Task, Agent
from src.models.tender import TenderList

def create_risk_task(agent: Agent, context: List[Task]) -> Task:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config",
        "tasks.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)["risk_task"]
        
    return Task(
        description=config["description"],
        expected_output=config["expected_output"],
        agent=agent,
        context=context,
        output_pydantic=TenderList,
    )
