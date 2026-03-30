"""ConsultEnv Models — Works with pydantic if available, falls back to dataclasses."""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

try:
    from pydantic import BaseModel, Field
    PYDANTIC = True
except ImportError:
    PYDANTIC = False
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self):
            r = {}
            for k, v in self.__dict__.items():
                if isinstance(v, BaseModel):
                    r[k] = v.model_dump()
                elif isinstance(v, list):
                    r[k] = [i.model_dump() if isinstance(i, BaseModel) else i for i in v]
                elif isinstance(v, dict):
                    r[k] = {dk: dv.model_dump() if isinstance(dv, BaseModel) else dv for dk, dv in v.items()}
                else:
                    r[k] = v
            return r
    def Field(**kw):
        return kw.get("default", kw.get("default_factory", lambda: None)())

class RoleInfo(BaseModel):
    def __init__(self, name="", rate_per_day=0, speed_overall=0.0, speed_spec_module=None,
                 speed_spec_value=0.0, quality_overall=0.0, quality_spec_module=None,
                 quality_spec_value=0.0, description="", **kw):
        super().__init__(name=name, rate_per_day=rate_per_day, speed_overall=speed_overall,
            speed_spec_module=speed_spec_module, speed_spec_value=speed_spec_value,
            quality_overall=quality_overall, quality_spec_module=quality_spec_module,
            quality_spec_value=quality_spec_value, description=description)

class ModuleInfo(BaseModel):
    def __init__(self, name="", base_days=0.0, base_quality=0.0, description="", available_parameters=None, **kw):
        super().__init__(name=name, base_days=base_days, base_quality=base_quality,
            description=description, available_parameters=available_parameters or {})

class ScenarioSpec(BaseModel):
    def __init__(self, id="", name="", client="", objective="", audience="", budget=0,
                 timeline_days=0, modules_required=None, quality_thresholds=None,
                 discovery_description=None, discovery_bonus=0.0, context="", **kw):
        super().__init__(id=id, name=name, client=client, objective=objective, audience=audience,
            budget=budget, timeline_days=timeline_days, modules_required=modules_required or [],
            quality_thresholds=quality_thresholds or {}, discovery_description=discovery_description,
            discovery_bonus=discovery_bonus, context=context)

class ResourceUsage(BaseModel):
    def __init__(self, budget_total=0, budget_spent=0, budget_remaining=0, days_total=0,
                 days_used=0.0, days_remaining=0.0, team_weekly_cost=0, team_total_cost=0,
                 external_costs=0, margin=0.0, **kw):
        super().__init__(budget_total=budget_total, budget_spent=budget_spent,
            budget_remaining=budget_remaining, days_total=days_total, days_used=days_used,
            days_remaining=days_remaining, team_weekly_cost=team_weekly_cost,
            team_total_cost=team_total_cost, external_costs=external_costs, margin=margin)

class ModuleOutput(BaseModel):
    def __init__(self, module="", summary="", details="", data_points=None, flags=None,
                 quality=0.0, quality_threshold=0.0, passed_threshold=False,
                 days_consumed=0.0, external_cost=0, **kw):
        super().__init__(module=module, summary=summary, details=details,
            data_points=data_points or {}, flags=flags or [], quality=quality,
            quality_threshold=quality_threshold, passed_threshold=passed_threshold,
            days_consumed=days_consumed, external_cost=external_cost)

class StepResult(BaseModel):
    def __init__(self, module="", output=None, reward=0.0, reward_breakdown=None, **kw):
        super().__init__(module=module, output=output, reward=reward,
            reward_breakdown=reward_breakdown or {})

class TeamComposition(BaseModel):
    def __init__(self, roles=None, weekly_cost=0, total_cost=0, **kw):
        super().__init__(roles=roles or [], weekly_cost=weekly_cost, total_cost=total_cost)

class ConsultAction(BaseModel):
    def __init__(self, action_type="", parameters=None, **kw):
        super().__init__(action_type=action_type, parameters=parameters or {})

class ConsultObservation(BaseModel):
    def __init__(self, scenario=None, available_actions=None, available_roles=None,
                 available_modules=None, step_index=0, team=None, pipeline_history=None,
                 resource_usage=None, latest_output=None, key_findings=None,
                 discovery_found=False, done=False, reward=0.0, total_reward=0.0, **kw):
        super().__init__(scenario=scenario, available_actions=available_actions or [],
            available_roles=available_roles or [], available_modules=available_modules or [],
            step_index=step_index, team=team, pipeline_history=pipeline_history or [],
            resource_usage=resource_usage, latest_output=latest_output,
            key_findings=key_findings or [], discovery_found=discovery_found,
            done=done, reward=reward, total_reward=total_reward)

class ConsultState(BaseModel):
    def __init__(self, scenario_id="", step_index=0, team_roles=None, completed_modules=None,
                 module_qualities=None, days_used=0.0, external_costs=0, team_cost=0,
                 discovery_found=False, senior_interviews_done=0, step_rewards=None,
                 done=False, metadata=None, **kw):
        super().__init__(scenario_id=scenario_id, step_index=step_index,
            team_roles=team_roles or [], completed_modules=completed_modules or [],
            module_qualities=module_qualities or {}, days_used=days_used,
            external_costs=external_costs, team_cost=team_cost,
            discovery_found=discovery_found, senior_interviews_done=senior_interviews_done,
            step_rewards=step_rewards or [], done=done, metadata=metadata or {})
