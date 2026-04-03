"""ConsultEnv — Main Environment Class implementing OpenEnv spec."""

import copy
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import (
        ConsultAction, ConsultObservation, ConsultState,
        ScenarioSpec, ResourceUsage, ModuleOutput, StepRecord,
        TeamComposition, RoleInfo, ModuleInfo,
    )
    from .tasks.scenarios import SCENARIOS
    from .simulator.team import (
        ROLES, OPTIONAL_ROLES, compute_team_cost,
        compute_speed_multiplier, compute_quality_boost, get_role_infos,
    )
    from .simulator.transition import execute_module, MODULES_BASE
    from .simulator.cascade import DEPENDENCIES
    from .rewards.step_reward import compute_step_reward
    from .rewards.terminal_reward import compute_terminal_reward
    from .tasks.outputs import get_output
except ImportError:
    from models import (
        ConsultAction, ConsultObservation, ConsultState,
        ScenarioSpec, ResourceUsage, ModuleOutput, StepRecord,
        TeamComposition, RoleInfo, ModuleInfo,
    )
    from server.tasks.scenarios import SCENARIOS
    from server.simulator.team import (
        ROLES, OPTIONAL_ROLES, compute_team_cost,
        compute_speed_multiplier, compute_quality_boost, get_role_infos,
    )
    from server.simulator.transition import execute_module, MODULES_BASE
    from server.simulator.cascade import DEPENDENCIES
    from server.rewards.step_reward import compute_step_reward
    from server.rewards.terminal_reward import compute_terminal_reward
    from server.tasks.outputs import get_output


class ConsultEnvEnvironment(Environment):
    """OpenEnv-compliant consulting engagement environment."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    # Normalization bounds: maps raw total score to [0, 1] for grader compliance
    _RAW_MIN = -1.0   # worst case: bad steps + severe timeline/budget penalty
    _RAW_MAX = 2.0    # best case: perfect steps + full terminal + discovery bonus

    @staticmethod
    def _normalize_total(raw: float) -> float:
        """Normalize raw episode total to [0, 1] for grader output."""
        return max(0.0, min(1.0, (raw - ConsultEnvEnvironment._RAW_MIN) /
                            (ConsultEnvEnvironment._RAW_MAX - ConsultEnvEnvironment._RAW_MIN)))

    def __init__(self):
        self._scenario_id = None
        self._state = None
        self._openenv_state = State(episode_id=str(uuid4()), step_count=0)

    def set_scenario(self, scenario_id: str):
        """Set scenario for next reset."""
        self._scenario_id = scenario_id

    def reset(self, scenario_id: str = None, seed: int = None) -> ConsultObservation:
        """Reset environment to initial state. Returns first observation."""
        if scenario_id:
            self._scenario_id = scenario_id
        
        if self._scenario_id is None:
            self._scenario_id = "benchmarking_study"

        if self._scenario_id not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {self._scenario_id}. Available: {list(SCENARIOS.keys())}")

        sc = SCENARIOS[self._scenario_id]

        self._state = {
            "scenario_id": self._scenario_id,
            "scenario": sc,
            "step_index": 0,
            "team_roles": ["Partner", "Manager"],
            "optional_roles": [],
            "team_staffed": False,
            "completed_modules": [],
            "module_qualities": {},
            "days_used": 0.0,
            "external_costs": 0,
            "team_weekly_cost": 0,
            "team_total_cost": 0,
            "discovery_found": False,
            "senior_interviews_done": 0,
            "step_rewards": [],
            "pipeline_history": [],
            "key_findings": [],
            "done": False,
        }

        self._openenv_state = State(episode_id=str(uuid4()), step_count=0)

        return self._build_observation(reward=0.0)

    def step(self, action: ConsultAction) -> ConsultObservation:
        """Execute one action. Returns updated observation."""
        if self._state is None:
            self.reset()
        if self._state["done"]:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        self._openenv_state.step_count += 1

        sc = self._state["scenario"]
        action_type = action.action_type
        params = action.parameters

        # ─── STAFF TEAM ACTION ───
        if action_type == "staff_team":
            if self._state["team_staffed"]:
                raise ValueError("Team already staffed. Cannot staff again.")

            opt = []
            if params.get("consultant"): opt.append("Consultant")
            if params.get("assoc_consultant"): opt.append("Assoc Consultant")
            if params.get("associate"): opt.append("Associate")
            if params.get("offshore_analyst"): opt.append("Offshore Analyst")
            if params.get("industry_expert"): opt.append("Industry Expert")

            self._state["optional_roles"] = opt
            self._state["team_roles"] = ["Partner", "Manager"] + opt
            self._state["team_staffed"] = True

            weekly, total = compute_team_cost(
                self._state["team_roles"],
                sc["partner_days_wk"],
                sc["timeline_days"],
            )
            self._state["team_weekly_cost"] = weekly
            self._state["team_total_cost"] = total

            # Staff team step has a small positive reward for valid staffing
            reward = 0.5
            self._state["step_rewards"].append(reward)
            self._state["step_index"] += 1

            return self._build_observation(reward=reward)

        # ─── MODULE ACTIONS ───
        if not self._state["team_staffed"]:
            raise ValueError("Must staff team first (action_type='staff_team').")

        module = action_type
        if module not in sc["modules_required"]:
            raise ValueError(f"Module '{module}' not required for this scenario. Required: {sc['modules_required']}")
        if module in self._state["completed_modules"]:
            raise ValueError(f"Module '{module}' already completed.")

        # Execute module
        has_expert = "Industry Expert" in self._state["team_roles"]
        result = execute_module(
            module=module,
            params=params,
            optional_roles=self._state["optional_roles"],
            completed_qualities=self._state["module_qualities"],
            case_modules=set(sc["modules_required"]),
            has_expert=has_expert,
            workshop_base_override=sc.get("workshop_base_override"),
        )

        # Update state
        self._state["days_used"] += result["actual_days"]
        self._state["external_costs"] += result["external_cost"]
        self._state["module_qualities"][module] = result["final_quality"]
        self._state["completed_modules"].append(module)

        # Track senior interviews for discovery
        if module == "interviews":
            count = params.get("interview_count", 8)
            sr = params.get("senior_ratio", 0.5)
            self._state["senior_interviews_done"] = int(count * sr)

        # Check discovery
        if module == "insight_gen" and sc.get("discovery_req"):
            needed = sc["discovery_req"]["senior_interviews"] - result["disc_reduce"]
            if self._state["senior_interviews_done"] >= needed:
                self._state["discovery_found"] = True
        elif module == "interviews" and sc.get("discovery_req"):
            if self._state["senior_interviews_done"] >= sc["discovery_req"]["senior_interviews"]:
                self._state["discovery_found"] = True

        # Get text output
        text_output = get_output(
            self._state["scenario_id"], module,
            method=params.get("method", "in_house"),
            qc=params.get("qc", False),
            int_count=params.get("interview_count"),
            sr_ratio=params.get("senior_ratio"),
        )

        # Add findings to key_findings
        for flag in text_output.get("flags", []):
            if flag not in self._state["key_findings"]:
                self._state["key_findings"].append(flag)

        # Build module output
        threshold = sc["thresholds"].get(module, 0)
        mod_output = ModuleOutput(
            module=module,
            summary=text_output.get("summary", f"Completed {module}"),
            details=text_output.get("details", ""),
            data_points=text_output.get("data_points", {}),
            flags=text_output.get("flags", []),
            quality=result["final_quality"],
            quality_threshold=threshold,
            passed_threshold=result["final_quality"] >= threshold,
            days_consumed=result["actual_days"],
            external_cost=result["external_cost"],
        )

        # Compute step reward
        # Module step index (0-based, not counting staff_team)
        module_step = len(self._state["completed_modules"]) - 1
        total_cost = self._state["team_total_cost"] + self._state["external_costs"]
        discretionary = sc["budget"] - self._state["team_total_cost"]

        step_rw = compute_step_reward(
            module=module,
            step_index=module_step,
            scenario_id=self._state["scenario_id"],
            completed_modules=set(self._state["completed_modules"]) - {module},
            case_modules=set(sc["modules_required"]),
            final_quality=result["final_quality"],
            threshold=threshold,
            ext_spent=self._state["external_costs"],
            discretionary_budget=discretionary,
            days_used=self._state["days_used"],
            timeline=sc["timeline_days"],
            total_modules=len(sc["modules_required"]),
        )

        reward = step_rw["reward"]
        self._state["step_rewards"].append(reward)

        # Store in pipeline history
        self._state["pipeline_history"].append(StepRecord(
            module=module,
            output=mod_output,
            reward=reward,
            reward_breakdown=step_rw,
        ))

        self._state["step_index"] += 1

        # Check if episode is done
        if set(self._state["completed_modules"]) == set(sc["modules_required"]):
            self._state["done"] = True

        return self._build_observation(reward=reward)

    @property
    def state(self) -> State:
        """OpenEnv state property."""
        return self._openenv_state

    def get_consult_state(self) -> ConsultState:
        """Return current internal state."""
        if self._state is None:
            self.reset()
        sc = self._state["scenario"]
        total_cost = self._state["team_total_cost"] + self._state["external_costs"]
        return ConsultState(
            scenario_id=self._state["scenario_id"],
            step_index=self._state["step_index"],
            team_roles=self._state["team_roles"],
            completed_modules=self._state["completed_modules"],
            module_qualities=self._state["module_qualities"],
            days_used=self._state["days_used"],
            external_costs=self._state["external_costs"],
            team_cost=self._state["team_total_cost"],
            discovery_found=self._state["discovery_found"],
            senior_interviews_done=self._state["senior_interviews_done"],
            step_rewards=self._state["step_rewards"],
            done=self._state["done"],
            metadata={
                "total_cost": total_cost,
                "budget": sc["budget"],
                "margin": (sc["budget"] - total_cost) / sc["budget"] if sc["budget"] > 0 else 0,
            },
        )

    def _build_observation(self, reward: float) -> ConsultObservation:
        """Build observation from current state."""
        sc = self._state["scenario"]
        total_cost = self._state["team_total_cost"] + self._state["external_costs"]
        margin = (sc["budget"] - total_cost) / sc["budget"] if sc["budget"] > 0 else 0

        # Available actions
        if not self._state["team_staffed"]:
            available = ["staff_team"]
        elif self._state["done"]:
            available = []
        else:
            completed = set(self._state["completed_modules"])
            available = [m for m in sc["modules_required"] if m not in completed]

        # Resource usage
        resource = ResourceUsage(
            budget_total=sc["budget"],
            budget_spent=total_cost,
            budget_remaining=sc["budget"] - total_cost,
            days_total=sc["timeline_days"],
            days_used=round(self._state["days_used"], 1),
            days_remaining=round(sc["timeline_days"] - self._state["days_used"], 1),
            team_weekly_cost=self._state["team_weekly_cost"],
            team_total_cost=self._state["team_total_cost"],
            external_costs=self._state["external_costs"],
            margin=round(margin, 4),
        ) if self._state["team_staffed"] else None

        # Team
        team = TeamComposition(
            roles=self._state["team_roles"],
            weekly_cost=self._state["team_weekly_cost"],
            total_cost=self._state["team_total_cost"],
        ) if self._state["team_staffed"] else None

        # Terminal reward if done
        total_reward = 0.0
        if self._state["done"]:
            budget_exceeded = total_cost > sc["budget"]
            term = compute_terminal_reward(
                module_qualities=self._state["module_qualities"],
                thresholds=sc["thresholds"],
                margin=margin,
                days_used=self._state["days_used"],
                timeline=sc["timeline_days"],
                discovery_found=self._state["discovery_found"],
                discovery_bonus=sc["discovery_bonus"],
                budget_exceeded=budget_exceeded,
            )
            # Total = avg(step_rewards) + terminal, then normalize to [0, 1]
            step_rews = [r for r in self._state["step_rewards"]]
            avg_step = sum(step_rews) / len(step_rews) if step_rews else 0
            raw_total = avg_step + term["terminal_reward"]
            total_reward = self._normalize_total(raw_total)
        else:
            # During episode: average of step rewards, clamped to [0, 1]
            step_rews = self._state["step_rewards"]
            avg = sum(step_rews) / len(step_rews) if step_rews else 0
            total_reward = max(0.0, min(1.0, avg))

        # Latest output
        latest = self._state["pipeline_history"][-1].output if self._state["pipeline_history"] else None

        # Scenario spec
        scenario_spec = ScenarioSpec(
            id=sc["id"], name=sc["name"], client=sc["client"],
            objective=sc["objective"], audience=sc["audience"],
            budget=sc["budget"], timeline_days=sc["timeline_days"],
            modules_required=sc["modules_required"],
            quality_thresholds=sc["thresholds"],
            discovery_description=sc.get("discovery_description"),
            discovery_bonus=sc["discovery_bonus"],
            context=sc.get("context", ""),
        )

        # Module infos
        module_infos = []
        for mod in sc["modules_required"]:
            mb = MODULES_BASE.get(mod, {})
            bd = mb.get("base_days", 0)
            if mod == "workshops" and sc.get("workshop_base_override"):
                bd = sc["workshop_base_override"]
            module_infos.append(ModuleInfo(
                name=mod, base_days=bd, base_quality=mb.get("base_quality", 0),
                description=f"Module: {mod}", available_parameters={},
            ))

        return ConsultObservation(
            scenario=scenario_spec,
            available_actions=available,
            available_roles=get_role_infos(),
            available_modules=module_infos,
            step_index=self._state["step_index"],
            team=team,
            pipeline_history=self._state["pipeline_history"],
            resource_usage=resource,
            latest_output=latest,
            key_findings=self._state["key_findings"],
            discovery_found=self._state["discovery_found"],
            done=self._state["done"],
            reward=round(max(0.0, min(1.0, reward)), 4),
            total_reward=round(total_reward, 4),
        )
