import os
import yaml
from crewai import Agent, LLM

RISK_CRITERIA = {
    "timeline":     "Срок до дедлайна: < 14 дней = HIGH risk/urgency, 14–60 = MEDIUM, > 60 = LOW",
    "competition":  "ICB = высокая конкуренция (HIGH), NCB = средняя (MEDIUM), RFQ = низкая (LOW)",
    "diameter":     "Нестандартный DN (560, 930) = риск отсутствия сертификата у composite.tj",
    "procurement":  "GPN = ранняя стадия (LOW risk, HIGH strategic opportunity), SPN = активный тендер (HIGH urgency)",
    "financier":    "IsDB/EFSD = правила менее знакомы, ВБ/АБР = стандартные",
}

def create_risk_analyst_agent(llm: LLM) -> Agent:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config",
        "agents.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)["risk_analyst_agent"]
        
    criteria_str = "\n".join([f"- {k}: {v}" for k, v in RISK_CRITERIA.items()])
    backstory = config["backstory"] + f"\n\nКритерии оценки рисков:\n{criteria_str}"
        
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=backstory,
        verbose=config.get("verbose", True),
        llm=llm,
        tools=[],
    )
