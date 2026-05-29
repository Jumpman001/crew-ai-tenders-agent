from pydantic import BaseModel, Field
from typing import Optional

class Tender(BaseModel):
    """Полная модель тендера/проекта — соответствует колонкам Excel-реестра."""

    # Идентификация
    num: int = Field(description="Порядковый номер в реестре")
    project_id: Optional[str] = Field(None, description="ID проекта (P177325, TJK-1044 и т.д.)")
    lot_ref: Optional[str] = Field(None, description="Номер лота (WSIP-W-PMU/001 и т.д.)")

    # Основные данные
    name: str = Field(description="Полное название проекта/лота")
    donor: str = Field(description="Финансирующее учреждение (ВБ, АБР, ЕБРР, IsDB и т.д.)")
    grant_loan_no: Optional[str] = Field(None, description="Номер гранта/кредита")
    executing_agency: str = Field(description="Исполнительное агентство")
    piu_pmu: Optional[str] = Field(None, description="ПИУ/ПМУ — орган управления проектом")

    # Статус и сроки
    status: str = Field(description="Статус: Активен / В исполнении / Не объявлен / Подготовка / GPN")
    period: Optional[str] = Field(None, description="Срок реализации (напр. до 2027-07)")
    duration_months: Optional[int] = Field(None, description="Продолжительность в месяцах")
    ifb_date: Optional[str] = Field(None, description="Дата публикации IFB/GPN/SPN")
    deadline_date: Optional[str] = Field(None, description="Дата закрытия тендера")

    # Подрядчик и закупки
    contractor: Optional[str] = Field(None, description="Компания-подрядчик (если известна)")
    procurement_method: Optional[str] = Field(None, description="NCB / ICB / RFQ / Direct")
    procurement_rules: Optional[str] = Field(None, description="Правила закупок донора")

    # Финансы
    total_budget: Optional[str] = Field(None, description="Общий бюджет лота в USD/EUR")
    composite_share: Optional[str] = Field(None, description="Потенциальная доля composite.tj (трубы)")

    # Технические параметры труб
    pipe_diameter_mm: Optional[str] = Field(None, description="Диаметр труб DN, мм")
    pipe_material: Optional[str] = Field(None, description="Материал: ПЭ / ПВХ / сталь / ВЧШГ / GRP")
    pipe_length_km: Optional[float] = Field(None, description="Протяжённость трубопровода, км")
    pipe_pressure_class: Optional[str] = Field(None, description="Класс давления PN")
    dn_400_confirmed: bool = Field(False, description="Подтверждено DN ≥ 400 мм")

    # Регион
    region: Optional[str] = Field(None, description="Регион: Хатлон / Душанбе / Согд / ГБАО")
    district: Optional[str] = Field(None, description="Район")

    # Контакты
    contact_name: Optional[str] = Field(None, description="ФИО контактного лица")
    contact_org: Optional[str] = Field(None, description="Организация")
    contact_email: Optional[str] = Field(None, description="Email")
    contact_phone: Optional[str] = Field(None, description="Телефон")
    contact_address: Optional[str] = Field(None, description="Адрес")

    # Риски
    risks: Optional[str] = Field(None, description="Риски и проблемы")
    urgency: str = Field("LOW", description="Срочность: HIGH / MEDIUM / LOW")
    suitability: Optional[str] = Field("LOW", description="Пригодность для Барса: HIGH / MEDIUM / LOW / NO")

    # Источники
    source_url: Optional[str] = Field(None, description="Ссылка на тендер")
    source_name: Optional[str] = Field(None, description="Название источника")
    last_updated: Optional[str] = Field(None, description="Дата последнего обновления")


class TenderList(BaseModel):
    tenders: list[Tender]

