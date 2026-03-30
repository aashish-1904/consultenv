"""
ConsultEnv Demo Runner — No LLM needed.
Runs hardcoded optimal strategies against all 4 scenarios,
printing full state at each step.

Usage:
  python demo_run.py                    # Run all 4 cases
  python demo_run.py benchmarking_study # Run specific case
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.environment import ConsultEnvironment
from models import ConsultAction

# ═══════════════════════════════════════════════════════════════
# OPTIMAL STRATEGIES (from stress testing)
# ═══════════════════════════════════════════════════════════════

STRATEGIES = {
    "benchmarking_study": {
        "name": "Easy — Benchmarking Study",
        "team": {"associate": True},
        "modules": [
            ("secondary", {"data_source": "ibisworld"}),
            ("benchmarking", {}),
            ("insight_gen", {}),
            ("presentation", {}),
        ],
    },
    "cost_optimization": {
        "name": "Medium — Cost Optimization",
        "team": {"assoc_consultant": True, "associate": True},
        "modules": [
            ("secondary", {"data_source": "ibisworld"}),
            ("interviews", {"interview_count": 8, "senior_ratio": 0.75, "qc": True}),
            ("benchmarking", {"qc": True}),
            ("data_modelling", {"tool": "alteryx"}),
            ("insight_gen", {"insight_method": "ai_assisted"}),
            ("presentation", {}),
        ],
    },
    "ops_transformation": {
        "name": "Hard — Ops Transformation",
        "team": {"assoc_consultant": True, "associate": True},
        "modules": [
            ("secondary", {"data_source": "ibisworld"}),
            ("interviews", {"interview_count": 8, "senior_ratio": 0.5, "qc": True}),
            ("benchmarking", {}),
            ("data_modelling", {}),
            ("insight_gen", {}),
            ("presentation", {}),
            ("workshops", {"facilitator": "agile_coach", "qc": True}),
        ],
    },
    "commercial_due_diligence": {
        "name": "Expert — Commercial Due Diligence",
        "team": {"industry_expert": True, "consultant": True, "assoc_consultant": True, "associate": True},
        "modules": [
            ("secondary", {"data_source": "bloomberg", "qc": True}),
            ("interviews", {"interview_count": 8, "senior_ratio": 0.5, "qc": True}),
            ("benchmarking", {}),
            ("data_modelling", {}),
            ("insight_gen", {}),
            ("presentation", {}),
            ("workshops", {"facilitator": "agile_coach", "qc": True}),
        ],
    },
}


def print_separator(char="═", width=80):
    print(char * width)


def print_observation(obs, step_label=""):
    """Pretty print an observation."""
    print(f"\n  {'─'*70}")
    print(f"  {step_label}")
    print(f"  {'─'*70}")
    
    if obs.team:
        print(f"  Team: {', '.join(obs.team.roles)}")
        print(f"  Team weekly cost: ${obs.team.weekly_cost:,} | Total: ${obs.team.total_cost:,}")
    
    if obs.resource_usage:
        ru = obs.resource_usage
        print(f"  Budget: ${ru.budget_spent:,} / ${ru.budget_total:,} (remaining: ${ru.budget_remaining:,})")
        print(f"  Days: {ru.days_used:.1f} / {ru.days_total} (remaining: {ru.days_remaining:.1f})")
        print(f"  Margin: {ru.margin:.1%}")
    
    if obs.latest_output:
        lo = obs.latest_output
        status = "✓ PASS" if lo.passed_threshold else "✗ FAIL"
        print(f"  Module: {lo.module}")
        print(f"  Quality: {lo.quality:.3f} (threshold: {lo.quality_threshold:.2f}) {status}")
        print(f"  Days consumed: {lo.days_consumed:.1f} | External cost: ${lo.external_cost:,}")
        print(f"  Summary: {lo.summary}")
        if lo.flags:
            print(f"  Flags: {lo.flags}")
    
    print(f"  Step reward: {obs.reward:.3f}")
    print(f"  Available actions: {obs.available_actions}")
    
    if obs.discovery_found:
        print(f"  ★ DISCOVERY FOUND!")
    
    if obs.done:
        print(f"\n  {'━'*70}")
        print(f"  EPISODE COMPLETE")
        print(f"  Total reward: {obs.total_reward:.3f}")
        print(f"  {'━'*70}")


def run_demo(scenario_id):
    """Run one demo episode with full state printing."""
    strategy = STRATEGIES[scenario_id]
    env = ConsultEnvironment()
    
    print_separator()
    print(f"  {strategy['name']}")
    print_separator()
    
    # Reset
    obs = env.reset(scenario_id)
    print(f"\n  Scenario: {obs.scenario.name}")
    print(f"  Client: {obs.scenario.client}")
    print(f"  Objective: {obs.scenario.objective}")
    print(f"  Budget: ${obs.scenario.budget:,} | Timeline: {obs.scenario.timeline_days} days")
    print(f"  Modules: {', '.join(obs.scenario.modules_required)}")
    print(f"  Thresholds: {obs.scenario.quality_thresholds}")
    if obs.scenario.discovery_description:
        print(f"  Discovery possible: {obs.scenario.discovery_description} (+{obs.scenario.discovery_bonus})")
    
    # Staff team
    action = ConsultAction(action_type="staff_team", parameters=strategy["team"])
    print(f"\n  → ACTION: staff_team {strategy['team']}")
    obs = env.step(action)
    print_observation(obs, "STEP 0: Staff Team")
    
    # Execute modules
    for i, (module, params) in enumerate(strategy["modules"]):
        action = ConsultAction(action_type=module, parameters=params)
        param_str = ", ".join(f"{k}={v}" for k, v in params.items()) if params else "defaults"
        print(f"\n  → ACTION: {module}({param_str})")
        obs = env.step(action)
        print_observation(obs, f"STEP {i+1}: {module}")
    
    # Print final state
    state = env.state()
    print(f"\n  FINAL STATE:")
    print(f"  Completed: {state.completed_modules}")
    print(f"  Qualities: {state.module_qualities}")
    print(f"  Days used: {state.days_used:.1f} / {obs.scenario.timeline_days}")
    print(f"  Total cost: ${state.metadata['total_cost']:,} / ${state.metadata['budget']:,}")
    print(f"  Margin: {state.metadata['margin']:.1%}")
    print(f"  Discovery: {state.discovery_found}")
    
    # Print reward breakdown
    print(f"\n  REWARD BREAKDOWN:")
    step_rewards = state.step_rewards
    avg_step = sum(step_rewards) / len(step_rewards) if step_rewards else 0
    terminal = obs.total_reward - avg_step
    print(f"  Step rewards: {[round(r, 3) for r in step_rewards]}")
    print(f"  Average step: {avg_step:.3f}")
    print(f"  Terminal: {terminal:.3f}")
    print(f"  TOTAL: {obs.total_reward:.3f}")
    
    print()
    return obs.total_reward


def run_demo_http(scenario_id, base_url="http://localhost:7860"):
    """Run demo via HTTP API (when server is running)."""
    import requests
    
    strategy = STRATEGIES[scenario_id]
    
    print_separator()
    print(f"  {strategy['name']} (via HTTP API)")
    print_separator()
    
    # Reset
    resp = requests.post(f"{base_url}/reset", json={"scenario_id": scenario_id})
    obs = resp.json()
    print(f"\n  Scenario: {obs['scenario']['name']}")
    print(f"  Budget: ${obs['scenario']['budget']:,} | Timeline: {obs['scenario']['timeline_days']}d")
    
    # Staff team
    resp = requests.post(f"{base_url}/step", json={
        "action": {"action_type": "staff_team", "parameters": strategy["team"]}
    })
    obs = resp.json()
    print(f"  Team staffed: {obs['team']['roles']}")
    
    # Execute modules
    for module, params in strategy["modules"]:
        resp = requests.post(f"{base_url}/step", json={
            "action": {"action_type": module, "parameters": params}
        })
        obs = resp.json()
        lo = obs.get("latest_output", {})
        status = "✓" if lo.get("passed_threshold") else "✗"
        print(f"  {module}: quality={lo.get('quality', 0):.3f} {status} | reward={obs['reward']:.3f}")
    
    print(f"\n  TOTAL REWARD: {obs['total_reward']:.3f}")
    print(f"  Days: {obs['resource_usage']['days_used']:.1f}/{obs['resource_usage']['days_total']}")
    print(f"  Margin: {obs['resource_usage']['margin']:.1%}")
    
    # Get state
    resp = requests.get(f"{base_url}/state")
    state = resp.json()
    print(f"  Discovery: {state['discovery_found']}")
    
    return obs['total_reward']


if __name__ == "__main__":
    tasks = sys.argv[1:] if len(sys.argv) > 1 else list(STRATEGIES.keys())
    
    # Check if we should use HTTP or direct
    use_http = "--http" in sys.argv
    if use_http:
        tasks = [t for t in tasks if t != "--http"]
    
    scores = {}
    for task_id in tasks:
        if task_id not in STRATEGIES:
            print(f"Unknown task: {task_id}")
            print(f"Available: {list(STRATEGIES.keys())}")
            continue
        
        if use_http:
            score = run_demo_http(task_id)
        else:
            score = run_demo(task_id)
        scores[task_id] = score
    
    if len(scores) > 1:
        print_separator()
        print("  SUMMARY")
        print_separator()
        for task_id, score in scores.items():
            print(f"  {task_id:<35} {score:.3f}")
        print(f"  {'AVERAGE':<35} {sum(scores.values())/len(scores):.3f}")
        print_separator()
