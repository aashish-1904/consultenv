"""Module sequencing validation and scoring."""

from server.simulator.cascade import DEPENDENCIES

IDEAL_ORDER = {
    "benchmarking_study": {"secondary": 0, "benchmarking": 1, "insight_gen": 2, "presentation": 3},
    "cost_optimization": {"secondary": 0, "interviews": 1, "benchmarking": 2, "data_modelling": 2, "insight_gen": 3, "presentation": 4},
    "ops_transformation": {"secondary": 0, "interviews": 1, "benchmarking": 2, "data_modelling": 2, "insight_gen": 3, "presentation": 4, "workshops": 5},
    "commercial_due_diligence": {"secondary": 0, "interviews": 1, "benchmarking": 2, "data_modelling": 2, "insight_gen": 3, "presentation": 4, "workshops": 5},
}


def compute_sequencing_score(module: str, step_index: int, scenario_id: str, 
                              completed_modules: set, case_modules: set) -> tuple:
    """Compute sequencing score and check dependency violations.
    
    Returns: (score: float, dependency_violation: bool)
    """
    # Check dependencies
    deps = DEPENDENCIES.get(module, [])
    unmet = [d for d in deps if d in case_modules and d not in completed_modules]
    if unmet:
        return 0.0, True
    
    # Position scoring
    ideal = IDEAL_ORDER.get(scenario_id, {})
    ideal_pos = ideal.get(module, 99)
    diff = abs(step_index - ideal_pos)
    
    if diff == 0:
        return 1.0, False
    elif diff == 1:
        return 0.7, False
    elif diff == 2:
        return 0.4, False
    else:
        return 0.1, False
