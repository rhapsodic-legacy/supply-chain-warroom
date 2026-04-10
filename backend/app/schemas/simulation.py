from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SimulationCreate(BaseModel):
    name: str
    description: str | None = None
    scenario_params: dict = {}
    iterations: int = 10000


class SimulationBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    created_at: datetime


class SimulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    scenario_params: str
    status: str
    iterations: int
    baseline_metrics: str | None
    mitigated_metrics: str | None
    comparison: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class SimulationCompareRequest(BaseModel):
    simulation_ids: list[str]


class SimulationCompareItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    baseline_metrics: str | None
    mitigated_metrics: str | None
    comparison: str | None


class SimulationCompareResponse(BaseModel):
    simulations: list[SimulationCompareItem]


class ExecutiveSummarySection(BaseModel):
    title: str
    content: str


class ExecutiveSummaryResponse(BaseModel):
    simulation_id: str
    simulation_name: str
    generated_at: datetime
    llm_tier: str
    sections: dict[str, ExecutiveSummarySection]
    raw_metrics: dict
