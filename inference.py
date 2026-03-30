"""ConsultEnv Baseline Inference Script.

Uses the OpenAI API client to run a simple agent against all 4 scenarios.
Reads from environment variables: API_BASE_URL, MODEL_NAME, HF_TOKEN
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai import OpenAI
from models import ConsultAction
from server.environment import ConsultEnvironment

# Read config from env
client = OpenAI(
    base_url=os.environ.get("API_BASE_URL", "https://api.openai.com/v1"),
    api_key=os.environ.get("HF_TOKEN", os.environ.get("OPENAI_API_KEY", "")),
)
model_name = os.environ.get("MODEL_NAME", "gpt-3.5-turbo")


SYSTEM_PROMPT = """You are an AI agent managing consulting engagements. You must make decisions about:
1. Team staffing (which optional roles to hire)
2. Module execution (which modules to run, in what order, with what parameters)

Your goal is to maximize the total score by balancing quality, profitability, and timeliness.

Key rules:
- First action must be "staff_team" 
- Execute modules in logical order (research before analysis, analysis before synthesis)
- QC adds 20% time but boosts quality (bigger boost on weaker modules)
- Upstream module quality cascades to downstream modules
- Budget overrun zeroes ALL terminal rewards
- Workshop module is isolated (only Expert specialist or Agile Coach affect it)

Respond with a JSON action object like:
{"action_type": "staff_team", "parameters": {"consultant": true, "associate": true}}
or
{"action_type": "secondary", "parameters": {"method": "in_house", "data_source": "ibisworld", "qc": false}}
"""


def parse_action(text: str) -> ConsultAction:
    """Parse LLM response into ConsultAction."""
    # Try to extract JSON from response
    text = text.strip()
    # Find JSON in response
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        json_str = text[start:end]
        try:
            data = json.loads(json_str)
            return ConsultAction(
                action_type=data.get("action_type", ""),
                parameters=data.get("parameters", {}),
            )
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse action from: {text[:200]}")


def build_prompt(obs_dict: dict) -> str:
    """Build a prompt from observation."""
    scenario = obs_dict["scenario"]
    parts = [
        f"SCENARIO: {scenario['name']}",
        f"Client: {scenario['client']}",
        f"Objective: {scenario['objective']}",
        f"Budget: ${scenario['budget']:,}",
        f"Timeline: {scenario['timeline_days']} days",
        f"Modules Required: {', '.join(scenario['modules_required'])}",
        f"Quality Thresholds: {scenario['quality_thresholds']}",
    ]
    
    if scenario.get("context"):
        parts.append(f"Context: {scenario['context']}")
    
    if obs_dict.get("resource_usage"):
        ru = obs_dict["resource_usage"]
        parts.append(f"\nRESOURCES: Budget remaining: ${ru['budget_remaining']:,} | Days remaining: {ru['days_remaining']}")
    
    if obs_dict.get("pipeline_history"):
        parts.append("\nCOMPLETED MODULES:")
        for step in obs_dict["pipeline_history"]:
            out = step["output"]
            parts.append(f"  - {out['module']}: quality={out['quality']:.3f} (threshold={out['quality_threshold']:.2f}) {'PASS' if out['passed_threshold'] else 'FAIL'}")
    
    if obs_dict.get("key_findings"):
        parts.append(f"\nKEY FINDINGS: {obs_dict['key_findings']}")
    
    parts.append(f"\nAVAILABLE ACTIONS: {obs_dict['available_actions']}")
    parts.append(f"Step: {obs_dict['step_index']}")
    
    if obs_dict.get("done"):
        parts.append(f"\nEPISODE COMPLETE. Total reward: {obs_dict['total_reward']:.3f}")
    else:
        parts.append("\nWhat action should we take next? Respond with a JSON action object.")
    
    return "\n".join(parts)


def run_task(env: ConsultEnvironment, task_id: str, verbose: bool = True) -> float:
    """Run one episode against a task."""
    obs = env.reset(task_id)
    obs_dict = obs.model_dump()
    done = False
    step = 0
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"TASK: {task_id}")
        print(f"{'='*60}")
    
    while not done:
        prompt = build_prompt(obs_dict)
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )
            action_text = response.choices[0].message.content
            action = parse_action(action_text)
        except Exception as e:
            if verbose:
                print(f"  LLM error at step {step}: {e}")
            # Fallback: use a simple heuristic
            action = _fallback_action(obs_dict, task_id)
        
        try:
            obs = env.step(action)
            obs_dict = obs.model_dump()
        except (ValueError, RuntimeError) as e:
            if verbose:
                print(f"  Step error: {e}")
            # Try fallback
            action = _fallback_action(obs_dict, task_id)
            obs = env.step(action)
            obs_dict = obs.model_dump()
        
        if verbose:
            if action.action_type == "staff_team":
                print(f"  Step {step}: staff_team → {action.parameters}")
            else:
                latest = obs_dict.get("latest_output", {})
                q = latest.get("quality", 0) if latest else 0
                print(f"  Step {step}: {action.action_type} → quality={q:.3f}, reward={obs_dict['reward']:.3f}")
        
        done = obs_dict["done"]
        step += 1
    
    total = obs_dict["total_reward"]
    if verbose:
        print(f"  TOTAL REWARD: {total:.3f}")
    return total


def _fallback_action(obs_dict: dict, task_id: str) -> ConsultAction:
    """Simple heuristic fallback when LLM fails."""
    available = obs_dict.get("available_actions", [])
    
    if "staff_team" in available:
        # Heuristic team based on task
        if task_id == "benchmarking_study":
            return ConsultAction(action_type="staff_team", parameters={"associate": True})
        elif task_id == "cost_optimization":
            return ConsultAction(action_type="staff_team", parameters={"assoc_consultant": True, "associate": True})
        elif task_id == "ops_transformation":
            return ConsultAction(action_type="staff_team", parameters={"assoc_consultant": True, "associate": True})
        else:  # CDD
            return ConsultAction(action_type="staff_team", parameters={
                "industry_expert": True, "consultant": True, "assoc_consultant": True, "associate": True
            })
    
    # Execute first available module
    if available:
        mod = available[0]
        params = {"qc": False}
        if mod == "interviews":
            params["interview_count"] = 8
            params["senior_ratio"] = 0.5
            params["qc"] = True
        elif mod == "workshops":
            if task_id == "ops_transformation":
                params["facilitator"] = "agile_coach"
                params["qc"] = True
            elif task_id == "commercial_due_diligence":
                params["facilitator"] = "agile_coach"  # Expert specialist is auto from team
                params["qc"] = True
        return ConsultAction(action_type=mod, parameters=params)
    
    raise RuntimeError("No available actions")


if __name__ == "__main__":
    env = ConsultEnvironment()
    tasks = ["benchmarking_study", "cost_optimization", "ops_transformation", "commercial_due_diligence"]
    
    print("ConsultEnv Baseline Inference")
    print(f"Model: {model_name}")
    print(f"API: {os.environ.get('API_BASE_URL', 'default')}")
    
    scores = {}
    for task_id in tasks:
        score = run_task(env, task_id)
        scores[task_id] = score
    
    print(f"\n{'='*60}")
    print("RESULTS:")
    for task_id, score in scores.items():
        print(f"  {task_id}: {score:.3f}")
    print(f"  AVERAGE: {sum(scores.values())/len(scores):.3f}")
