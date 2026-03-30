"""Module execution engine — computes time, cost, quality for each module."""

from server.simulator.team import compute_speed_multiplier, compute_quality_boost
from server.simulator.cascade import compute_cascade_factor

# ═══════════════════════════════════════════════════════════════
# PARAMETER REGISTRIES
# ═══════════════════════════════════════════════════════════════

MODULES_BASE = {
    "secondary":      {"base_days": 4.5, "base_quality": 0.60},
    "benchmarking":   {"base_days": 4.5, "base_quality": 0.60},
    "interviews":     {"base_days": 6.0, "base_quality": 0.55},
    "data_modelling": {"base_days": 7.5, "base_quality": 0.65},
    "insight_gen":    {"base_days": 4.5, "base_quality": 0.55},
    "presentation":   {"base_days": 3.0, "base_quality": 0.60},
    "workshops":      {"base_days": 7.5, "base_quality": 0.50},
}

DATA_SOURCES = {
    "internal":          {"cost": 0,     "quality_add": 0.00, "time_mult": 1.0},
    "public_filings":    {"cost": 0,     "quality_add": 0.03, "time_mult": 1.2},
    "trade_publications":{"cost": 500,   "quality_add": 0.04, "time_mult": 1.0},
    "ibisworld":         {"cost": 2000,  "quality_add": 0.05, "time_mult": 1.0},
    "sp_capital_iq":     {"cost": 8000,  "quality_add": 0.08, "time_mult": 1.0},
    "factiva":           {"cost": 5000,  "quality_add": 0.06, "time_mult": 1.0},
    "bloomberg":         {"cost": 15000, "quality_add": 0.15, "time_mult": 1.0},
}

DM_TOOLS = {
    "excel":   {"cost": 0,    "time_mult": 1.0, "quality_add": 0.00, "requires_qc": False, "no_qc_penalty": 0},
    "alteryx": {"cost": 8000, "time_mult": 0.6, "quality_add": 0.08, "requires_qc": False, "no_qc_penalty": 0},
    "copilot": {"cost": 3000, "time_mult": 0.4, "quality_add": -0.10, "requires_qc": True,  "no_qc_penalty": -0.10},
}

INSIGHT_METHODS = {
    "manual":         {"cost": 0,    "time_mult": 1.0, "quality_add": 0.00, "disc_reduce": 0},
    "ai_assisted":    {"cost": 2000, "time_mult": 0.7, "quality_add": 0.03, "disc_reduce": 0},
    "junior_ai_deep": {"cost": 8000, "time_mult": 0.5, "quality_add": 0.05, "disc_reduce": 2},
}

PRES_METHODS = {
    "in_house":  {"cost": 0,   "time_mult": 1.0, "quality_mult": 1.0, "quality_add": 0},
    "graphics":  {"cost": 2000, "time_mult": 1.3, "quality_mult": 1.0, "quality_add": 0.15},
    "ai_generated": {"cost": 500, "time_mult": 0.4, "quality_mult": 0.6, "quality_add": 0},
}

WORKSHOP_FACILITATORS = {
    "internal":     {"cost_per_day": 0,    "speed_mult": 1.0,  "quality_add": 0.00, "needs_expert": False},
    "agile_coach":  {"cost_per_day": 6500, "speed_mult": 0.85, "quality_add": 0.25, "needs_expert": False},
    "expert_led":   {"cost_per_day": 0,    "speed_mult": 1.0,  "quality_add": 0.00, "needs_expert": True},
}

INTERVIEW_Q_SCALE = {2: 0.40, 4: 0.60, 6: 0.75, 8: 0.85, 10: 0.90, 12: 0.93, 15: 0.95, 20: 0.97}


def _get_int_q(n):
    for k in sorted(INTERVIEW_Q_SCALE.keys()):
        if n <= k:
            return INTERVIEW_Q_SCALE[k]
    return 0.97


def _get_int_extra_days(n):
    if n <= 4: return 0
    elif n <= 8: return 1
    elif n <= 12: return 2
    elif n <= 16: return 3
    return 4


def _dynamic_qc_boost(quality):
    if quality <= 0.50: return 0.20
    elif quality <= 0.60: return 0.17
    elif quality <= 0.70: return 0.14
    elif quality <= 0.80: return 0.11
    elif quality <= 0.90: return 0.07
    return 0.03


def execute_module(
    module: str,
    params: dict,
    optional_roles: list,
    completed_qualities: dict,
    case_modules: set,
    has_expert: bool,
    workshop_base_override: float = None,
) -> dict:
    """Execute a module and return results.
    
    Returns dict with: actual_days, external_cost, raw_quality, cascade_factor,
    pre_qc_quality, qc_boost, final_quality, discovery_info
    """
    base = MODULES_BASE[module]
    bd = base["base_days"]
    if module == "workshops" and workshop_base_override:
        bd = workshop_base_override
    
    ext_cost = 0
    quality_add = 0.0
    quality_mult = 1.0
    time_mult = 1.0
    disc_reduce = 0
    
    # Module-specific parameter handling
    if module == "secondary":
        method = params.get("method", "in_house")
        if method == "offshore":
            time_mult *= 0.7; ext_cost += 3000
        elif method == "vendor":
            time_mult *= 0.5; ext_cost += 5000; quality_mult *= 1.1
        ds = DATA_SOURCES.get(params.get("data_source", "internal"), DATA_SOURCES["internal"])
        ext_cost += ds["cost"]; quality_add += ds["quality_add"]; time_mult *= ds["time_mult"]
    
    elif module == "benchmarking":
        method = params.get("method", "in_house")
        if method == "offshore":
            time_mult *= 0.7; ext_cost += 3000
        elif method == "vendor":
            time_mult *= 0.5; ext_cost += 5000; quality_mult *= 1.1
    
    elif module == "interviews":
        count = params.get("interview_count", 8)
        sr = params.get("senior_ratio", 0.5)
        bd += _get_int_extra_days(count)
        n_senior = int(count * sr)
        n_mid = count - n_senior
        ext_cost += n_senior * 800 + n_mid * 500
    
    elif module == "data_modelling":
        tool = DM_TOOLS.get(params.get("tool", "excel"), DM_TOOLS["excel"])
        time_mult *= tool["time_mult"]; ext_cost += tool["cost"]; quality_add += tool["quality_add"]
        if tool["requires_qc"] and not params.get("qc", False):
            quality_add += tool["no_qc_penalty"]
    
    elif module == "insight_gen":
        im = INSIGHT_METHODS.get(params.get("insight_method", "manual"), INSIGHT_METHODS["manual"])
        time_mult *= im["time_mult"]; ext_cost += im["cost"]; quality_add += im["quality_add"]
        disc_reduce = im["disc_reduce"]
    
    elif module == "presentation":
        pm = PRES_METHODS.get(params.get("pres_method", "in_house"), PRES_METHODS["in_house"])
        time_mult *= pm["time_mult"]; ext_cost += pm["cost"]
        quality_mult *= pm["quality_mult"]; quality_add += pm["quality_add"]
        if params.get("pres_method") == "ai_generated" and params.get("qc") and params.get("pres_qc_rounds", 1) > 1:
            for _ in range(1, min(params.get("pres_qc_rounds", 1), 3)):
                quality_add += 0.10; time_mult *= 1.15
    
    elif module == "workshops":
        fac_key = params.get("facilitator", "internal")
        fac = WORKSHOP_FACILITATORS.get(fac_key, WORKSHOP_FACILITATORS["internal"])
        if fac["needs_expert"] and not has_expert:
            quality_add += -0.15  # penalty for claiming expert-led without expert
        else:
            quality_add += fac["quality_add"]
        time_mult *= fac["speed_mult"]
    
    # QC time multiplier
    qc_active = params.get("qc", False)
    qc_time = 1.20 if qc_active else 1.0
    
    # Team speed
    team_speed = compute_speed_multiplier(module, optional_roles)
    
    # Actual days
    actual_days = bd * team_speed * time_mult * qc_time
    
    # Workshop facilitator per-day cost
    if module == "workshops":
        fac_key = params.get("facilitator", "internal")
        fac = WORKSHOP_FACILITATORS.get(fac_key, WORKSHOP_FACILITATORS["internal"])
        ext_cost += int(fac["cost_per_day"] * actual_days)
    
    # Quality calculation
    if module == "interviews":
        count = params.get("interview_count", 8)
        sr = params.get("senior_ratio", 0.5)
        count_mult = _get_int_q(count)
        seniority_mult = 1.0 + (sr * 0.3)
        raw_quality = base["base_quality"] * count_mult * seniority_mult + compute_quality_boost(module, optional_roles) + quality_add
    else:
        raw_quality = (base["base_quality"] + compute_quality_boost(module, optional_roles) + quality_add) * quality_mult
    
    # Cascade
    cf = compute_cascade_factor(module, completed_qualities, case_modules)
    pre_qc = raw_quality * cf
    
    # QC boost
    qc_boost = _dynamic_qc_boost(pre_qc) if qc_active else 0.0
    
    final_quality = min(max(pre_qc + qc_boost, 0.0), 1.0)
    
    return {
        "actual_days": round(actual_days, 2),
        "external_cost": ext_cost,
        "raw_quality": round(raw_quality, 4),
        "cascade_factor": round(cf, 4),
        "pre_qc_quality": round(pre_qc, 4),
        "qc_boost": round(qc_boost, 4),
        "final_quality": round(final_quality, 4),
        "disc_reduce": disc_reduce,
    }
