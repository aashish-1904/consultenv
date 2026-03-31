"""Data models for the ConsultEnv Environment."""

from typing import List, Optional, Dict, Any
from openenv.core.env_server.types import Action, Observation
from pydantic import BaseModel, Field


class ConsultAction(Action):
    """Action the agent takes — staff team or execute a module."""
    action_type: str = Field(..., description="staff_team, secondary, benchmarking, interviews, data_modelling, insight_gen, presentation, or workshops")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Module-specific parameters")


class ModuleOutput(BaseModel):
    module: str = ""
    quality: float = 0.0
    quality_threshold: float = 0.0
    passed_threshold: bool = False
    days_consumed: float = 0.0
    external_cost: int = 0
    summary: str = ""
    details: str = ""
    data_points: Dict[str, Any] = Field(default_factory=dict)
    flags: List[str] = Field(default_factory=list)


class StepRecord(BaseModel):
    module: str = ""
    output: ModuleOutput = Field(default_factory=ModuleOutput)
    reward: float = 0.0
    reward_breakdown: Dict[str, Any] = Field(default_factory=dict)


class ScenarioSpec(BaseModel):
    id: str = ""
    name: str = ""
    client: str = ""
    objective: str = ""
    budget: int = 0
    timeline_days: int = 0
    audience: str = ""
    modules_required: List[str] = Field(default_factory=list)
    quality_thresholds: Dict[str, float] = Field(default_factory=dict)
    discovery_description: Optional[str] = None
    discovery_bonus: float = 0.0
    context: str = ""


class TeamComposition(BaseModel):
    roles: List[str] = Field(default_factory=list)
    weekly_cost: int = 0
    total_cost: int = 0


class ResourceUsage(BaseModel):
    budget_total: int = 0
    budget_spent: int = 0
    budget_remaining: int = 0
    days_total: int = 0
    days_used: float = 0.0
    days_remaining: float = 0.0
    team_weekly_cost: int = 0
    team_total_cost: int = 0
    external_costs: int = 0
    margin: float = 0.0


class RoleInfo(BaseModel):
    name: str = ""
    billing_rate: int = 0
    description: str = ""
    speed_overall: float = 0.0
    speed_specialty: Optional[str] = None
    speed_specialty_value: float = 0.0
    quality_overall: float = 0.0
    quality_specialty: Optional[str] = None
    quality_specialty_value: float = 0.0


class ModuleInfo(BaseModel):
    name: str = ""
    base_days: float = 0.0
    base_quality: float = 0.0
    description: str = ""
    available_parameters: Dict[str, Any] = Field(default_factory=dict)


class ConsultObservation(Observation):
    """What the agent sees after each step."""
    scenario: ScenarioSpec = Field(default_factory=ScenarioSpec)
    available_actions: List[str] = Field(default_factory=list)
    available_roles: List[RoleInfo] = Field(default_factory=list)
    available_modules: List[ModuleInfo] = Field(default_factory=list)
    step_index: int = 0
    team: Optional[TeamComposition] = None
    pipeline_history: List[StepRecord] = Field(default_factory=list)
    resource_usage: Optional[ResourceUsage] = None
    latest_output: Optional[ModuleOutput] = None
    key_findings: List[str] = Field(default_factory=list)
    discovery_found: bool = False
    done: bool = False
    reward: float = 0.0
    total_reward: float = 0.0


class ConsultState(BaseModel):
    scenario_id: str = ""
    step_index: int = 0
    completed_modules: List[str] = Field(default_factory=list)
    module_qualities: Dict[str, float] = Field(default_factory=dict)
    team_roles: List[str] = Field(default_factory=list)
    budget_spent: int = 0
    budget_remaining: int = 0
    days_used: float = 0.0
    days_remaining: float = 0.0
    margin: float = 0.0
    external_costs: int = 0
    team_cost: int = 0
    discovery_found: bool = False
    senior_interviews_done: int = 0
    done: bool = False
    step_rewards: List[float] = Field(default_factory=list)
    total_reward: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
