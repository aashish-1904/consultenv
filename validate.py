"""
ConsultEnv Validator — Simulates what hackathon judges will check.

Run against live server:
    python validate.py                          # default localhost:8000
    python validate.py https://user-consultenv.hf.space   # against HF Space

Checks:
  1. Server is alive (GET /, GET /health)
  2. OpenEnv spec compliance (reset/step/state endpoints)
  3. All 4 tasks discoverable and runnable
  4. Grader produces scores in valid range
  5. Scores are deterministic (same run = same score)
  6. Episode boundaries work correctly
  7. Error handling (bad actions rejected)
  8. Dockerfile and inference.py exist
"""

import sys
import os
import json
import time

# Can run in two modes: HTTP (against live server) or Direct (import environment)
MODE = "direct"  # default
BASE_URL = "http://localhost:8000"

if len(sys.argv) > 1:
    arg = sys.argv[1]
    if arg.startswith("http"):
        MODE = "http"
        BASE_URL = arg.rstrip("/")
    elif arg == "--direct":
        MODE = "direct"

PASS = 0
FAIL = 0
WARN = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")

def warn(name, detail=""):
    global WARN
    WARN += 1
    print(f"  ⚠️  {name} — {detail}")


# ═══════════════════════════════════════════════════════════════
# HTTP MODE
# ═══════════════════════════════════════════════════════════════

def validate_http():
    import requests

    print(f"\nValidating against: {BASE_URL}")
    print(f"{'='*70}")

    # ─── 1. Server alive ───
    print("\n1. SERVER HEALTH")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=10)
        check("GET / returns 200", r.status_code == 200, f"got {r.status_code}")
        data = r.json()
        check("Root returns name", "name" in data, f"keys: {list(data.keys())}")
        check("Root returns tasks list", "tasks" in data and len(data["tasks"]) >= 3,
              f"tasks: {data.get('tasks')}")
    except Exception as e:
        check("Server reachable", False, str(e))
        print("\n  Cannot proceed — server not reachable.")
        return

    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        check("GET /health returns 200", r.status_code == 200)
        check("Health status ok", r.json().get("status") == "ok")
    except Exception as e:
        check("Health endpoint", False, str(e))

    # ─── 2. Reset endpoint ───
    print("\n2. RESET ENDPOINT")
    try:
        r = requests.post(f"{BASE_URL}/reset", json={"scenario_id": "benchmarking_study"}, timeout=10)
        check("POST /reset returns 200", r.status_code == 200, f"got {r.status_code}")
        obs = r.json()
        check("Reset returns scenario", "scenario" in obs)
        check("Reset returns available_actions", "available_actions" in obs)
        check("Reset step_index is 0", obs.get("step_index") == 0, f"got {obs.get('step_index')}")
        check("Reset done is False", obs.get("done") == False)
        check("First available action is staff_team", "staff_team" in obs.get("available_actions", []))
    except Exception as e:
        check("Reset endpoint", False, str(e))

    # Bad scenario
    try:
        r = requests.post(f"{BASE_URL}/reset", json={"scenario_id": "nonexistent_task"}, timeout=5)
        check("Bad scenario returns error (not 200)", r.status_code != 200, f"got {r.status_code}")
    except Exception as e:
        check("Bad scenario handling", False, str(e))

    # ─── 3. Step endpoint ───
    print("\n3. STEP ENDPOINT")
    try:
        # Reset first
        requests.post(f"{BASE_URL}/reset", json={"scenario_id": "benchmarking_study"})

        # Staff team
        r = requests.post(f"{BASE_URL}/step", json={
            "action": {"action_type": "staff_team", "parameters": {"associate": True}}
        }, timeout=10)
        check("Staff team step returns 200", r.status_code == 200)
        obs = r.json()
        check("Team is populated", obs.get("team") is not None)
        check("Resource usage populated", obs.get("resource_usage") is not None)
        check("Step reward > 0", obs.get("reward", 0) > 0, f"got {obs.get('reward')}")

        # Execute module
        r = requests.post(f"{BASE_URL}/step", json={
            "action": {"action_type": "secondary", "parameters": {"data_source": "ibisworld"}}
        }, timeout=10)
        check("Module step returns 200", r.status_code == 200)
        obs = r.json()
        check("Latest output populated", obs.get("latest_output") is not None)
        lo = obs.get("latest_output", {})
        check("Output has quality", "quality" in lo and isinstance(lo["quality"], (int, float)))
        check("Output has threshold", "quality_threshold" in lo)
        check("Output has passed_threshold", "passed_threshold" in lo)
        check("Quality in valid range", 0 <= lo.get("quality", -1) <= 1.0, f"got {lo.get('quality')}")
    except Exception as e:
        check("Step endpoint", False, str(e))

    # ─── 4. State endpoint ───
    print("\n4. STATE ENDPOINT")
    try:
        r = requests.get(f"{BASE_URL}/state", timeout=5)
        check("GET /state returns 200", r.status_code == 200)
        state = r.json()
        check("State has scenario_id", "scenario_id" in state)
        check("State has completed_modules", "completed_modules" in state)
        check("State has module_qualities", "module_qualities" in state)
    except Exception as e:
        check("State endpoint", False, str(e))

    # ─── 5. Full episode on all 4 tasks ───
    print("\n5. FULL EPISODES — ALL TASKS")
    task_scores = run_all_tasks_http(requests)

    # ─── 6. Determinism ───
    print("\n6. DETERMINISM CHECK")
    task_scores_2 = run_all_tasks_http(requests, quiet=True)
    for tid in task_scores:
        check(f"{tid} deterministic",
              abs(task_scores[tid] - task_scores_2[tid]) < 0.001,
              f"run1={task_scores[tid]:.3f}, run2={task_scores_2[tid]:.3f}")

    # ─── 7. Error handling ───
    print("\n7. ERROR HANDLING")
    try:
        requests.post(f"{BASE_URL}/reset", json={"scenario_id": "benchmarking_study"})
        # Try module before staffing
        r = requests.post(f"{BASE_URL}/step", json={
            "action": {"action_type": "secondary", "parameters": {}}
        })
        check("Module before staff_team rejected", r.status_code != 200, f"got {r.status_code}")
    except:
        pass

    try:
        requests.post(f"{BASE_URL}/reset", json={"scenario_id": "benchmarking_study"})
        requests.post(f"{BASE_URL}/step", json={
            "action": {"action_type": "staff_team", "parameters": {"associate": True}}
        })
        # Try invalid module
        r = requests.post(f"{BASE_URL}/step", json={
            "action": {"action_type": "workshops", "parameters": {}}
        })
        check("Invalid module for case rejected", r.status_code != 200, f"got {r.status_code}")
    except:
        pass


def run_all_tasks_http(requests, quiet=False):
    tasks = {
        "benchmarking_study": {
            "team": {"associate": True},
            "modules": [
                ("secondary", {"data_source": "ibisworld"}),
                ("benchmarking", {}),
                ("insight_gen", {}),
                ("presentation", {}),
            ]
        },
        "cost_optimization": {
            "team": {"assoc_consultant": True, "associate": True},
            "modules": [
                ("secondary", {"data_source": "ibisworld"}),
                ("interviews", {"interview_count": 8, "senior_ratio": 0.75, "qc": True}),
                ("benchmarking", {}),
                ("data_modelling", {"tool": "alteryx"}),
                ("insight_gen", {"insight_method": "ai_assisted"}),
                ("presentation", {}),
            ]
        },
        "ops_transformation": {
            "team": {"assoc_consultant": True, "associate": True},
            "modules": [
                ("secondary", {"data_source": "ibisworld"}),
                ("interviews", {"interview_count": 8, "senior_ratio": 0.5, "qc": True}),
                ("benchmarking", {}),
                ("data_modelling", {}),
                ("insight_gen", {}),
                ("presentation", {}),
                ("workshops", {"facilitator": "agile_coach", "qc": True}),
            ]
        },
        "commercial_due_diligence": {
            "team": {"industry_expert": True, "consultant": True, "assoc_consultant": True, "associate": True},
            "modules": [
                ("secondary", {"data_source": "bloomberg", "qc": True}),
                ("interviews", {"interview_count": 8, "senior_ratio": 0.5, "qc": True}),
                ("benchmarking", {}),
                ("data_modelling", {}),
                ("insight_gen", {}),
                ("presentation", {}),
                ("workshops", {"facilitator": "agile_coach", "qc": True}),
            ]
        },
    }

    scores = {}
    for task_id, strategy in tasks.items():
        r = requests.post(f"{BASE_URL}/reset", json={"scenario_id": task_id})
        obs = r.json()

        r = requests.post(f"{BASE_URL}/step", json={
            "action": {"action_type": "staff_team", "parameters": strategy["team"]}
        })

        for mod, params in strategy["modules"]:
            r = requests.post(f"{BASE_URL}/step", json={
                "action": {"action_type": mod, "parameters": params}
            })
            obs = r.json()

        score = obs.get("total_reward", 0)
        scores[task_id] = score

        if not quiet:
            done = obs.get("done", False)
            check(f"{task_id}: episode completes", done == True, f"done={done}")
            check(f"{task_id}: score > 0", score > 0, f"score={score}")
            check(f"{task_id}: score in reasonable range", -1 < score < 3, f"score={score}")
            print(f"       Score: {score:.3f}")

    return scores


# ═══════════════════════════════════════════════════════════════
# DIRECT MODE (no server needed)
# ═══════════════════════════════════════════════════════════════

def validate_direct():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    print(f"\nValidating in direct mode (no HTTP)")
    print(f"{'='*70}")

    # ─── 1. Imports ───
    print("\n1. IMPORTS & FILE CHECKS")
    try:
        from server.consultenv_environment import ConsultEnvEnvironment as ConsultEnvironment
        from models import ConsultAction, ConsultObservation, ConsultState
        check("Environment imports", True)
    except Exception as e:
        check("Environment imports", False, str(e))
        return

    check("openenv.yaml exists", os.path.exists("openenv.yaml"))
    check("inference.py exists", os.path.exists("inference.py"))
    check("Dockerfile exists", os.path.exists("Dockerfile"))
    check("requirements.txt exists", os.path.exists("requirements.txt"))
    check("README.md exists", os.path.exists("README.md"))
    check("demo_run.py exists", os.path.exists("demo_run.py"))
    check("test_integration.py exists", os.path.exists("test_integration.py"))

    # Check openenv.yaml content
    import yaml
    try:
        with open("openenv.yaml") as f:
            oe = yaml.safe_load(f)
        check("openenv.yaml has name", "name" in oe, f"keys: {list(oe.keys())}")
        check("openenv.yaml has tasks", "tasks" in oe and len(oe["tasks"]) >= 3,
              f"tasks: {len(oe.get('tasks', []))}")
        for task in oe.get("tasks", []):
            check(f"Task '{task['id']}' has difficulty", "difficulty" in task)
    except ImportError:
        warn("PyYAML not installed — skipping yaml validation")
    except Exception as e:
        check("openenv.yaml valid", False, str(e))

    # ─── 2. Reset ───
    print("\n2. RESET")
    env = ConsultEnvironment()

    obs = env.reset("benchmarking_study")
    check("Reset returns observation", obs is not None)
    check("Observation has scenario", hasattr(obs, 'scenario') and obs.scenario is not None)
    check("Observation has available_actions", hasattr(obs, 'available_actions'))
    check("Step index is 0 after reset", obs.step_index == 0, f"got {obs.step_index}")
    check("Done is False after reset", obs.done == False)
    check("staff_team is available", "staff_team" in obs.available_actions)

    # Bad scenario
    try:
        env.reset("nonexistent")
        check("Bad scenario raises error", False, "no exception raised")
    except ValueError:
        check("Bad scenario raises ValueError", True)

    # ─── 3. Step ───
    print("\n3. STEP")
    env.reset("benchmarking_study")
    obs = env.step(ConsultAction(action_type="staff_team", parameters={"associate": True}))
    check("Staff team works", obs.team is not None)
    check("Team has roles", len(obs.team.roles) > 0, f"roles: {obs.team.roles}")
    check("Resource usage populated", obs.resource_usage is not None)
    check("Reward is numeric", isinstance(obs.reward, (int, float)))

    obs = env.step(ConsultAction(action_type="secondary", parameters={"data_source": "ibisworld"}))
    check("Module step works", obs.latest_output is not None)
    check("Quality in range [0,1]", 0 <= obs.latest_output.quality <= 1.0,
          f"got {obs.latest_output.quality}")
    check("Has threshold", obs.latest_output.quality_threshold >= 0)
    check("Has passed_threshold flag", isinstance(obs.latest_output.passed_threshold, bool))

    # ─── 4. State ───
    print("\n4. STATE")
    state = env.get_consult_state()
    check("State has scenario_id", hasattr(state, 'scenario_id'))
    check("State has completed_modules", hasattr(state, 'completed_modules'))
    check("State has module_qualities", hasattr(state, 'module_qualities'))
    check("State has step_rewards", hasattr(state, 'step_rewards'))
    check("Completed modules match", "secondary" in state.completed_modules)
    # Also verify openenv State property works
    oe_state = env.state
    check("OpenEnv state has episode_id", hasattr(oe_state, 'episode_id'))
    check("OpenEnv state has step_count", hasattr(oe_state, 'step_count'))

    # ─── 5. Full episodes ───
    print("\n5. FULL EPISODES — ALL TASKS")
    scores = run_all_tasks_direct(env, ConsultAction)

    # ─── 6. Determinism ───
    print("\n6. DETERMINISM CHECK")
    scores_2 = run_all_tasks_direct(env, ConsultAction, quiet=True)
    for tid in scores:
        check(f"{tid} deterministic",
              abs(scores[tid] - scores_2[tid]) < 0.001,
              f"run1={scores[tid]:.3f}, run2={scores_2[tid]:.3f}")

    # ─── 7. Error handling ───
    print("\n7. ERROR HANDLING")
    env.reset("benchmarking_study")
    try:
        env.step(ConsultAction(action_type="secondary", parameters={}))
        check("Module before staff_team rejected", False, "no exception")
    except ValueError:
        check("Module before staff_team rejected", True)

    env.reset("benchmarking_study")
    env.step(ConsultAction(action_type="staff_team", parameters={"associate": True}))
    try:
        env.step(ConsultAction(action_type="workshops", parameters={}))
        check("Invalid module for easy case rejected", False, "no exception")
    except ValueError:
        check("Invalid module for easy case rejected", True)

    # Double staff
    env.reset("benchmarking_study")
    env.step(ConsultAction(action_type="staff_team", parameters={"associate": True}))
    try:
        env.step(ConsultAction(action_type="staff_team", parameters={"associate": True}))
        check("Double staff_team rejected", False, "no exception")
    except ValueError:
        check("Double staff_team rejected", True)

    # Duplicate module
    env.reset("benchmarking_study")
    env.step(ConsultAction(action_type="staff_team", parameters={"associate": True}))
    env.step(ConsultAction(action_type="secondary", parameters={}))
    try:
        env.step(ConsultAction(action_type="secondary", parameters={}))
        check("Duplicate module rejected", False, "no exception")
    except ValueError:
        check("Duplicate module rejected", True)

    # Step after done
    env.reset("benchmarking_study")
    env.step(ConsultAction(action_type="staff_team", parameters={"associate": True}))
    env.step(ConsultAction(action_type="secondary", parameters={}))
    env.step(ConsultAction(action_type="benchmarking", parameters={}))
    env.step(ConsultAction(action_type="insight_gen", parameters={}))
    obs = env.step(ConsultAction(action_type="presentation", parameters={}))
    check("Episode is done", obs.done == True)
    try:
        env.step(ConsultAction(action_type="secondary", parameters={}))
        check("Step after done rejected", False, "no exception")
    except RuntimeError:
        check("Step after done rejected", True)

    # ─── 8. Reward properties ───
    print("\n8. REWARD PROPERTIES")
    env.reset("benchmarking_study")
    env.step(ConsultAction(action_type="staff_team", parameters={"associate": True}))

    rewards = []
    for mod in ["secondary", "benchmarking", "insight_gen", "presentation"]:
        obs = env.step(ConsultAction(action_type=mod, parameters={}))
        rewards.append(obs.reward)

    check("All step rewards are numeric", all(isinstance(r, (int, float)) for r in rewards))
    check("Step rewards vary (not constant)", len(set(round(r, 3) for r in rewards)) > 1,
          f"rewards: {rewards}")
    check("Final total_reward is numeric", isinstance(obs.total_reward, (int, float)))
    check("Episode done at end", obs.done == True)

    # Grader range check
    all_scores = list(scores.values())
    check("All scores > -1.0", all(s > -1.0 for s in all_scores), f"scores: {all_scores}")
    check("All scores < 3.0", all(s < 3.0 for s in all_scores), f"scores: {all_scores}")
    check("Scores are not all the same", len(set(round(s, 2) for s in all_scores)) > 1,
          f"scores: {all_scores}")


def run_all_tasks_direct(env, ConsultAction, quiet=False):
    tasks = {
        "benchmarking_study": {
            "team": {"associate": True},
            "modules": [
                ("secondary", {"data_source": "ibisworld"}),
                ("benchmarking", {}),
                ("insight_gen", {}),
                ("presentation", {}),
            ]
        },
        "cost_optimization": {
            "team": {"assoc_consultant": True, "associate": True},
            "modules": [
                ("secondary", {"data_source": "ibisworld"}),
                ("interviews", {"interview_count": 8, "senior_ratio": 0.75, "qc": True}),
                ("benchmarking", {}),
                ("data_modelling", {"tool": "alteryx"}),
                ("insight_gen", {"insight_method": "ai_assisted"}),
                ("presentation", {}),
            ]
        },
        "ops_transformation": {
            "team": {"assoc_consultant": True, "associate": True},
            "modules": [
                ("secondary", {"data_source": "ibisworld"}),
                ("interviews", {"interview_count": 8, "senior_ratio": 0.5, "qc": True}),
                ("benchmarking", {}),
                ("data_modelling", {}),
                ("insight_gen", {}),
                ("presentation", {}),
                ("workshops", {"facilitator": "agile_coach", "qc": True}),
            ]
        },
        "commercial_due_diligence": {
            "team": {"industry_expert": True, "consultant": True, "assoc_consultant": True, "associate": True},
            "modules": [
                ("secondary", {"data_source": "bloomberg", "qc": True}),
                ("interviews", {"interview_count": 8, "senior_ratio": 0.5, "qc": True}),
                ("benchmarking", {}),
                ("data_modelling", {}),
                ("insight_gen", {}),
                ("presentation", {}),
                ("workshops", {"facilitator": "agile_coach", "qc": True}),
            ]
        },
    }

    scores = {}
    for task_id, strategy in tasks.items():
        env.reset(task_id)
        env.step(ConsultAction(action_type="staff_team", parameters=strategy["team"]))

        for mod, params in strategy["modules"]:
            obs = env.step(ConsultAction(action_type=mod, parameters=params))

        score = obs.total_reward
        scores[task_id] = score

        if not quiet:
            check(f"{task_id}: episode completes", obs.done == True)
            check(f"{task_id}: score > 0", score > 0, f"score={score}")
            check(f"{task_id}: score in reasonable range", -1 < score < 3, f"score={score}")
            print(f"       Score: {score:.3f}")

    return scores


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║         ConsultEnv — Hackathon Submission Validator             ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    start = time.time()

    if MODE == "http":
        validate_http()
    else:
        validate_direct()

    elapsed = time.time() - start

    print(f"\n{'='*70}")
    print(f"VALIDATION COMPLETE in {elapsed:.1f}s")
    print(f"  ✅ Passed: {PASS}")
    print(f"  ❌ Failed: {FAIL}")
    if WARN:
        print(f"  ⚠️  Warnings: {WARN}")
    print(f"{'='*70}")

    if FAIL == 0:
        print("🎉 ALL CHECKS PASSED — Ready for submission!")
    else:
        print(f"⚠️  {FAIL} checks failed — fix before submitting.")

    sys.exit(0 if FAIL == 0 else 1)
