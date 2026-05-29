import os
import yaml
from crewai import Agent, LLM
from src.tools import DuckDuckGoSearchTool, WebScraperTool

KNOWN_CONTACTS = {
    "WSIP-1 / RWSSP (ВБ)": {
        "piu": "MIDP PMU — ЦУП MIDP",
        "director": "Саидвализода А.Р.",
        "email": "pmu@wsip-1.tj",
        "phone": "+992372331330",
        "address": "56, ул. Н. Карабаева, Душанбе",
    },
    "IsDB TJK-1013 (Хатлон)": {
        "piu": "ПИУ «DVIP»",
        "director": "Рахматзода Муродали",
        "email": "нет данных",
        "phone": "нет данных",
        "address": "10, ул. Бохтар, 3 этаж, Душанбе",
    },
    "IsDB TJK-1044 (Пяндж)": {
        "piu": "ALRI РТ",
        "director": "Давлатзода Зафарбек",
        "email": "alri.tj@mail.ru",
        "phone": "+992 37 235 76 68",
        "address": "5/1, ул. Шамси, Душанбе",
    },
    "SWIM / МЭВР (ВБ)": {
        "piu": "PIU при МЭВР РТ",
        "email": "pmu.mewr@gmail.com",
        "address": "Душанбе, ул. Шамси 5/1",
    },
    "ЕБРР Яван": {
        "piu": "ЕБРР Душанбе",
        "email": "dushanbe@ebrd.com",
        "phone": "+992 37 224 61 17",
        "address": "ул. Айни 14, 4 этаж, Душанбе",
        "portal": "https://ecepp.ebrd.com",
    },
    "ADB (53109, 50347)": {
        "piu": "ADB Tajikistan Resident Mission",
        "portal": "https://www.adb.org/countries/tajikistan/projects",
        "rss": "https://www.adb.org/rss/projects/tenders?country=TAJ",
    },
    "EFSD": {
        "portal": "https://efsd.org/en/purchases/",
        "edb": "https://eabr.org/en/projects/countries/tajikistan/",
    },
}

def create_contact_agent(llm: LLM) -> Agent:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config",
        "agents.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)["contact_agent"]
    
    # Inject KNOWN_CONTACTS into the backstory to provide base knowledge
    contacts_str = "\n".join([
        f"- {name}: PIU={c.get('piu','N/A')}, Director={c.get('director','N/A')}, Email={c.get('email','N/A')}, Phone={c.get('phone','N/A')}, Address={c.get('address','N/A')}"
        for name, c in KNOWN_CONTACTS.items()
    ])
    
    backstory = config["backstory"] + f"\n\nБаза известных контактов (используй её в первую очередь):\n{contacts_str}"
        
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=backstory,
        verbose=config.get("verbose", True),
        max_iter=config.get("max_iter", 5),
        llm=llm,
        tools=[
            DuckDuckGoSearchTool(),
            WebScraperTool(),
        ],
    )
