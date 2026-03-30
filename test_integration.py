"""
ConsultEnv Integration Test — Verifies all environment logic.
Runs without pydantic by testing the simulation engine directly.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import simulation components directly
from server.simulator.team import ROLES, compute_team_cost, compute_speed_multiplier, compute_quality_boost
from server.simulator.cascade import compute_cascade_factor, DEPENDENCIES
from server.simulator.transition import execute_module, MODULES_BASE
from server.rewards.step_reward import compute_step_reward
from server.rewards.terminal_reward import compute_terminal_reward
from server.rules.sequencing import compute_sequencing_score
from server.tasks.scenarios import SCENARIOS

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} — {detail}")


def run_episode(scenario_id, team_opt, module_sequence):
    """Run a full episode and return results."""
    sc = SCENARIOS[scenario_id]
    roles = ["Partner", "Manager"] + team_opt
    weekly, total_team = compute_team_cost(roles, sc["partner_days_wk"], sc["timeline_days"])
    
    completed_q = {}
    completed_set = set()
    days_used = 0.0
    ext_cost = 0
    step_rewards = []
    n_senior = 0
    discovery = False
    has_expert = "Industry Expert" in roles
    case_mods = set(sc["modules_required"])
    
    for si, (mod, params) in enumerate(module_sequence):
        result = execute_module(
            module=mod, params=params, optional_roles=team_opt,
            completed_qualities=completed_q, case_modules=case_mods,
            has_expert=has_expert, workshop_base_override=sc.get("workshop_base_override"),
        )
        
        days_used += result["actual_days"]
        ext_cost += result["external_cost"]
        completed_q[mod] = result["final_quality"]
        completed_set.add(mod)
        
        if mod == "interviews":
            n_senior = int(params.get("interview_count", 8) * params.get("senior_ratio", 0.5))
        
        if mod == "insight_gen" and sc.get("discovery_req"):
            needed = sc["discovery_req"]["senior_interviews"] - result["disc_reduce"]
            if n_senior >= needed:
                discovery = True
        if mod == "interviews" and sc.get("discovery_req"):
            if n_senior >= sc["discovery_req"]["senior_interviews"]:
                discovery = True
        
        thr = sc["thresholds"].get(mod, 0)
        sr = compute_step_reward(
            module=mod, step_index=si, scenario_id=scenario_id,
            completed_modules=completed_set - {mod}, case_modules=case_mods,
            final_quality=result["final_quality"], threshold=thr,
            ext_spent=ext_cost, discretionary_budget=sc["budget"] - total_team,
            days_used=days_used, timeline=sc["timeline_days"],
            total_modules=len(sc["modules_required"]),
        )
        step_rewards.append(sr["reward"])
    
    total_cost = total_team + ext_cost
    margin = (sc["budget"] - total_cost) / sc["budget"]
    
    term = compute_terminal_reward(
        module_qualities=completed_q, thresholds=sc["thresholds"],
        margin=margin, days_used=days_used, timeline=sc["timeline_days"],
        discovery_found=discovery, discovery_bonus=sc["discovery_bonus"],
        budget_exceeded=total_cost > sc["budget"],
    )
    
    avg_step = sum(step_rewards) / len(step_rewards) if step_rewards else 0
    total_score = avg_step + term["terminal_reward"]
    
    return {
        "total_score": round(total_score, 3),
        "avg_step": round(avg_step, 3),
        "terminal": round(term["terminal_reward"], 3),
        "margin": round(margin, 3),
        "days": round(days_used, 1),
        "qualities": {k: round(v, 3) for k, v in completed_q.items()},
        "below": term["modules_below_threshold"],
        "discovery": discovery,
        "budget_exceeded": total_cost > sc["budget"],
        "total_cost": total_cost,
        "ext_cost": ext_cost,
    }


print("=" * 70)
print("CONSULTENV INTEGRATION TEST")
print("=" * 70)

# ═══════════ TEST 1: Team Cost Calculations ═══════════
print("\n1. TEAM COST CALCULATIONS")
w, t = compute_team_cost(["Partner", "Manager", "Associate"], 2, 15)
check("Easy team weekly", w == 10000*2 + 7000*5 + 2500*5, f"got {w}")
check("Easy team total (3 weeks)", t == w * 3, f"got {t}")

w, t = compute_team_cost(["Partner", "Manager", "Industry Expert", "Consultant", "Assoc Consultant", "Associate"], 4, 30)
check("Hard team weekly", w == 10000*4 + 7000*5 + 8000*5 + 5000*5 + 3500*5 + 2500*5, f"got {w}")

# ═══════════ TEST 2: Speed Multipliers ═══════════
print("\n2. SPEED MULTIPLIERS")
s = compute_speed_multiplier("secondary", ["Associate"])
check("Associate speeds up secondary", s < 1.0, f"got {s}")
check("Associate secondary specialist", abs(s - 0.80) < 0.01, f"got {s}, expected 0.80")

s = compute_speed_multiplier("workshops", ["Associate", "Consultant"])
check("Workshops isolated from team speed", s == 1.0, f"got {s}")

s = compute_speed_multiplier("insight_gen", ["Consultant"])
check("Consultant speeds up insight_gen", abs(s - 0.80) < 0.01, f"got {s}")

# ═══════════ TEST 3: Quality Boosts ═══════════
print("\n3. QUALITY BOOSTS")
q = compute_quality_boost("presentation", ["Consultant"])
check("Consultant boosts presentation quality", abs(q - 0.20) < 0.01, f"got {q}")

q = compute_quality_boost("workshops", ["Consultant", "Associate"])
check("Workshops isolated: no overall boosts", q == 0.0, f"got {q}")

q = compute_quality_boost("workshops", ["Industry Expert"])
check("Expert boosts workshop quality", abs(q - 0.30) < 0.01, f"got {q}")

q = compute_quality_boost("benchmarking", ["Associate"])
check("Associate boosts benchmarking", abs(q - 0.20) < 0.01, f"got {q}")

# ═══════════ TEST 4: Cascade Factor ═══════════
print("\n4. CASCADE FACTOR")
cf = compute_cascade_factor("secondary", {}, {"secondary"})
check("Secondary: no cascade (no deps)", cf == 1.0, f"got {cf}")

cf = compute_cascade_factor("benchmarking", {"secondary": 0.70}, {"secondary", "benchmarking"})
check("Benchmarking cascade with 0.70 secondary", abs(cf - 1.0) < 0.01, f"got {cf}")

cf = compute_cascade_factor("benchmarking", {"secondary": 0.90}, {"secondary", "benchmarking"})
check("Benchmarking cascade boosted with good secondary", cf > 1.0, f"got {cf}")

cf = compute_cascade_factor("benchmarking", {"secondary": 0.50}, {"secondary", "benchmarking"})
check("Benchmarking cascade penalized with bad secondary", cf < 1.0, f"got {cf}")

# Workshop cascade cap
cf_normal = compute_cascade_factor("insight_gen", {"secondary": 0.90, "benchmarking": 0.85, "interviews": 0.80, "data_modelling": 0.85}, 
                                    {"secondary", "benchmarking", "interviews", "data_modelling", "insight_gen"})
cf_ws = compute_cascade_factor("workshops", {"insight_gen": 0.90, "interviews": 0.80},
                                {"insight_gen", "interviews", "workshops"})
check("Workshop cascade is capped (< normal)", cf_ws < cf_normal, f"ws={cf_ws}, normal={cf_normal}")

# ═══════════ TEST 5: Module Execution ═══════════
print("\n5. MODULE EXECUTION")

r = execute_module("secondary", {"data_source": "bloomberg"}, ["Associate"], {}, {"secondary"}, False)
check("Bloomberg adds quality", r["raw_quality"] > 0.70, f"got {r['raw_quality']}")
check("Bloomberg costs $15K", r["external_cost"] == 15000, f"got {r['external_cost']}")

r = execute_module("data_modelling", {"tool": "copilot", "qc": False}, ["Offshore Analyst"], {}, {"data_modelling"}, False)
check("Copilot without QC has penalty", r["raw_quality"] <= 0.60, f"got {r['raw_quality']}")

r_qc = execute_module("data_modelling", {"tool": "copilot", "qc": True}, ["Offshore Analyst"], {}, {"data_modelling"}, False)
check("Copilot with QC recovers quality", r_qc["final_quality"] > r["final_quality"], f"noQC={r['final_quality']}, QC={r_qc['final_quality']}")

# Workshop isolation
r = execute_module("workshops", {"facilitator": "agile_coach", "qc": True}, ["Consultant", "Associate"], 
                   {"insight_gen": 0.85, "interviews": 0.80}, {"insight_gen", "interviews", "workshops"}, False)
check("Coach adds workshop quality", r["raw_quality"] > 0.70, f"got {r['raw_quality']}")

r_expert = execute_module("workshops", {"facilitator": "expert_led"}, ["Industry Expert", "Consultant"], 
                          {"insight_gen": 0.85, "interviews": 0.80}, {"insight_gen", "interviews", "workshops"}, True)
check("Expert-led raw > coach raw", r_expert["raw_quality"] > r["raw_quality"], 
      f"expert={r_expert['raw_quality']}, coach={r['raw_quality']}")

# ═══════════ TEST 6: Sequencing ═══════════
print("\n6. SEQUENCING")
score, dep = compute_sequencing_score("secondary", 0, "benchmarking_study", set(), {"secondary", "benchmarking", "insight_gen", "presentation"})
check("Secondary at position 0 = perfect", score == 1.0)

score, dep = compute_sequencing_score("presentation", 0, "benchmarking_study", set(), {"secondary", "benchmarking", "insight_gen", "presentation"})
check("Presentation at 0 has dep violation", dep == True)
check("Dep violation score = 0", score == 0.0)

score, dep = compute_sequencing_score("benchmarking", 2, "benchmarking_study", {"secondary"}, {"secondary", "benchmarking", "insight_gen", "presentation"})
check("Benchmarking at 2 (1 off)", abs(score - 0.7) < 0.01, f"got {score}")

# ═══════════ TEST 7: Full Episode — Easy ═══════════
print("\n7. FULL EPISODE — EASY")
r = run_episode("benchmarking_study", ["Associate"], [
    ("secondary", {"data_source": "ibisworld"}),
    ("benchmarking", {}),
    ("insight_gen", {}),
    ("presentation", {}),
])
check("Easy completes", r["total_score"] > 0, f"score={r['total_score']}")
check("Easy no budget bust", not r["budget_exceeded"])
check("Easy positive margin", r["margin"] > 0.30, f"margin={r['margin']}")
check("Easy days within timeline", r["days"] <= 15, f"days={r['days']}")
print(f"  → Score: {r['total_score']} | Margin: {r['margin']:.1%} | Days: {r['days']}/15")

# ═══════════ TEST 8: Full Episode — Medium ═══════════
print("\n8. FULL EPISODE — MEDIUM (smart tools)")
r = run_episode("cost_optimization", ["Assoc Consultant", "Associate"], [
    ("secondary", {"data_source": "ibisworld"}),
    ("interviews", {"interview_count": 8, "senior_ratio": 0.75, "qc": True}),
    ("benchmarking", {"qc": True}),
    ("data_modelling", {"tool": "alteryx"}),
    ("insight_gen", {"insight_method": "ai_assisted"}),
    ("presentation", {}),
])
check("Medium positive score", r["total_score"] > 1.0, f"score={r['total_score']}")
check("Medium discovery found", r["discovery"] == True, "6 senior interviews should trigger")
check("Medium margin ok", r["margin"] > 0.25, f"margin={r['margin']}")
print(f"  → Score: {r['total_score']} | Margin: {r['margin']:.1%} | Days: {r['days']}/25 | Disc: {r['discovery']}")

# ═══════════ TEST 9: Full Episode — Hard (Ops Transform) ═══════════
print("\n9. FULL EPISODE — HARD (Ops Transform)")
r_coach = run_episode("ops_transformation", ["Assoc Consultant", "Associate"], [
    ("secondary", {"data_source": "ibisworld"}),
    ("interviews", {"interview_count": 8, "senior_ratio": 0.5, "qc": True}),
    ("benchmarking", {}),
    ("data_modelling", {}),
    ("insight_gen", {}),
    ("presentation", {}),
    ("workshops", {"facilitator": "agile_coach", "qc": True}),
])
print(f"  → Coach: Score: {r_coach['total_score']} | WS quality: {r_coach['qualities'].get('workshops', 'N/A')} | Margin: {r_coach['margin']:.1%}")

r_expert = run_episode("ops_transformation", ["Industry Expert", "Assoc Consultant", "Associate"], [
    ("secondary", {"data_source": "ibisworld"}),
    ("interviews", {"interview_count": 8, "senior_ratio": 0.5, "qc": True}),
    ("benchmarking", {}),
    ("data_modelling", {}),
    ("insight_gen", {}),
    ("presentation", {}),
    ("workshops", {"facilitator": "expert_led"}),
])
print(f"  → Expert: Score: {r_expert['total_score']} | WS quality: {r_expert['qualities'].get('workshops', 'N/A')} | Margin: {r_expert['margin']:.1%}")

check("Coach beats Expert on ops_transform (or close)", 
      r_coach["total_score"] >= r_expert["total_score"] - 0.3,
      f"coach={r_coach['total_score']}, expert={r_expert['total_score']}")

# ═══════════ TEST 10: Full Episode — Expert (CDD) ═══════════
print("\n10. FULL EPISODE — EXPERT (CDD)")
r_both = run_episode("commercial_due_diligence", ["Industry Expert", "Consultant", "Assoc Consultant", "Associate"], [
    ("secondary", {"data_source": "bloomberg", "qc": True}),
    ("interviews", {"interview_count": 8, "senior_ratio": 0.5, "qc": True}),
    ("benchmarking", {}),
    ("data_modelling", {}),
    ("insight_gen", {}),
    ("presentation", {}),
    ("workshops", {"facilitator": "agile_coach", "qc": True}),
])
print(f"  → Expert+Coach: Score: {r_both['total_score']} | WS: {r_both['qualities'].get('workshops', 'N/A')} | Margin: {r_both['margin']:.1%} | Fails: {r_both['below']}")

r_expert_only = run_episode("commercial_due_diligence", ["Industry Expert", "Consultant", "Assoc Consultant", "Associate"], [
    ("secondary", {"qc": True}),
    ("interviews", {"interview_count": 8, "senior_ratio": 0.5, "qc": True}),
    ("benchmarking", {}),
    ("data_modelling", {}),
    ("insight_gen", {}),
    ("presentation", {}),
    ("workshops", {"facilitator": "expert_led"}),
])
print(f"  → Expert only: Score: {r_expert_only['total_score']} | WS: {r_expert_only['qualities'].get('workshops', 'N/A')} | Margin: {r_expert_only['margin']:.1%} | Fails: {r_expert_only['below']}")

r_no_expert = run_episode("commercial_due_diligence", ["Consultant", "Assoc Consultant", "Associate"], [
    ("secondary", {"qc": True}),
    ("interviews", {"interview_count": 8, "senior_ratio": 0.5, "qc": True}),
    ("benchmarking", {}),
    ("data_modelling", {}),
    ("insight_gen", {}),
    ("presentation", {}),
    ("workshops", {"facilitator": "internal", "qc": True}),
])
print(f"  → No Expert: Score: {r_no_expert['total_score']} | WS: {r_no_expert['qualities'].get('workshops', 'N/A')} | Margin: {r_no_expert['margin']:.1%} | Fails: {r_no_expert['below']}")

ws_expert_only = r_expert_only['qualities'].get('workshops', 0)
ws_both = r_both['qualities'].get('workshops', 0)
check("Expert+Coach WS passes 0.95", ws_both >= 0.95, f"got {ws_both}")
check("Expert-only WS fails 0.95", ws_expert_only < 0.95, f"got {ws_expert_only}")
check("Expert+Coach beats Expert-only on CDD", r_both['total_score'] > r_expert_only['total_score'],
      f"both={r_both['total_score']}, expert_only={r_expert_only['total_score']}")

# ═══════════ TEST 11: Budget Nuclear ═══════════
print("\n11. BUDGET NUCLEAR")
r = run_episode("benchmarking_study", ["Industry Expert", "Consultant", "Assoc Consultant", "Associate", "Offshore Analyst"], [
    ("secondary", {"data_source": "bloomberg"}),
    ("benchmarking", {"method": "vendor"}),
    ("insight_gen", {"insight_method": "junior_ai_deep"}),
    ("presentation", {"pres_method": "graphics"}),
])
is_bust = r["total_cost"] > 380250
check("Overstaffed easy busts budget", is_bust, f"total={r['total_cost']}")
if is_bust:
    check("Budget bust negative terminal", r["terminal"] < 0, f"terminal={r['terminal']}")

# ═══════════ TEST 12: Wrong Order Penalty ═══════════
print("\n12. WRONG ORDER PENALTY")
r_correct = run_episode("benchmarking_study", ["Associate"], [
    ("secondary", {}), ("benchmarking", {}), ("insight_gen", {}), ("presentation", {}),
])
r_wrong = run_episode("benchmarking_study", ["Associate"], [
    ("presentation", {}), ("secondary", {}), ("benchmarking", {}), ("insight_gen", {}),
])
check("Correct order beats wrong order", r_correct["total_score"] > r_wrong["total_score"],
      f"correct={r_correct['total_score']}, wrong={r_wrong['total_score']}")
check("Wrong order significantly worse", r_correct["total_score"] - r_wrong["total_score"] > 0.2,
      f"diff={r_correct['total_score'] - r_wrong['total_score']}")

# ═══════════ TEST 13: QC Value ═══════════
print("\n13. QC VALUE")
r_noqc = run_episode("benchmarking_study", ["Associate"], [
    ("secondary", {}), ("benchmarking", {}), ("insight_gen", {}), ("presentation", {}),
])
r_qc = run_episode("benchmarking_study", ["Associate"], [
    ("secondary", {"qc": True}), ("benchmarking", {}), ("insight_gen", {}), ("presentation", {}),
])
check("QC on secondary improves downstream quality",
      r_qc["qualities"]["benchmarking"] >= r_noqc["qualities"]["benchmarking"],
      f"qc_bench={r_qc['qualities']['benchmarking']}, noqc_bench={r_noqc['qualities']['benchmarking']}")

# ═══════════ TEST 14: Discovery Mechanic ═══════════
print("\n14. DISCOVERY MECHANIC")
r_disc = run_episode("cost_optimization", ["Assoc Consultant", "Associate"], [
    ("secondary", {}), ("interviews", {"interview_count": 8, "senior_ratio": 1.0, "qc": True}),
    ("benchmarking", {}), ("data_modelling", {}), ("insight_gen", {}), ("presentation", {}),
])
r_nodisc = run_episode("cost_optimization", ["Assoc Consultant", "Associate"], [
    ("secondary", {}), ("interviews", {"interview_count": 4, "senior_ratio": 0.0}),
    ("benchmarking", {}), ("data_modelling", {}), ("insight_gen", {}), ("presentation", {}),
])
check("Senior interviews trigger discovery", r_disc["discovery"] == True)
check("Low interviews miss discovery", r_nodisc["discovery"] == False)
check("Discovery adds bonus to score", r_disc["total_score"] > r_nodisc["total_score"],
      f"disc={r_disc['total_score']}, nodisc={r_nodisc['total_score']}")

# ═══════════ SUMMARY ═══════════
print(f"\n{'='*70}")
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
print(f"{'='*70}")
if FAIL == 0:
    print("ALL TESTS PASSED ✓")
else:
    print(f"⚠ {FAIL} TESTS FAILED")
