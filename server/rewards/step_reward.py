"""Per-step reward computation."""

from server.rules.sequencing import compute_sequencing_score


def compute_step_reward(
    module: str,
    step_index: int,
    scenario_id: str,
    completed_modules: set,
    case_modules: set,
    final_quality: float,
    threshold: float,
    ext_spent: int,
    discretionary_budget: int,
    days_used: float,
    timeline: int,
    total_modules: int,
) -> dict:
    """Compute per-step reward.
    
    step_reward = (sequencing × 0.35) + (quality × 0.40) + (efficiency × 0.25) + penalties
    """
    # Sequencing
    seq_score, dep_violation = compute_sequencing_score(
        module, step_index, scenario_id, completed_modules, case_modules
    )
    dep_penalty = -0.2 if dep_violation else 0.0
    
    # Quality
    qual_score = final_quality
    # Scale threshold penalty by how far below threshold (bigger miss = harsher penalty)
    if final_quality < threshold:
        deficit = threshold - final_quality
        thresh_penalty = -0.1 * (1 + deficit * 2)
    else:
        thresh_penalty = 0.0
    
    # Efficiency
    modules_done_ratio = (step_index + 1) / total_modules
    
    if discretionary_budget > 0 and ext_spent > 0:
        budget_eff = min(1.0, modules_done_ratio / max(ext_spent / max(discretionary_budget, 1), 0.01))
    else:
        budget_eff = 1.0
    
    if timeline > 0:
        time_eff = min(1.0, modules_done_ratio / max(days_used / timeline, 0.01))
    else:
        time_eff = 1.0
    
    eff_score = (budget_eff + time_eff) / 2
    
    # Total
    reward = (seq_score * 0.35) + (qual_score * 0.40) + (eff_score * 0.25) + dep_penalty + thresh_penalty
    
    return {
        "reward": round(reward, 4),
        "sequencing_score": round(seq_score, 4),
        "quality_score": round(qual_score, 4),
        "efficiency_score": round(eff_score, 4),
        "dependency_penalty": dep_penalty,
        "threshold_penalty": thresh_penalty,
        "dependency_violation": dep_violation,
    }
