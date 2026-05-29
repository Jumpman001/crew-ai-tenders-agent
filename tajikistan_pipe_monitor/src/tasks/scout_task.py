import os
import yaml
from crewai import Task, Agent

def create_scout_task(agent: Agent) -> Task:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config",
        "tasks.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)["scout_task"]
        
    return Task(
        description=config["description"],
        expected_output=config["expected_output"],
        agent=agent,
    )
