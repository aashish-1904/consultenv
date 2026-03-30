"""Cascading quality dependency calculations."""

DEPENDENCIES = {
    "secondary": [],
    "benchmarking": ["secondary"],
    "interviews": [],
    "data_modelling": ["secondary", "interviews"],
    "insight_gen": ["secondary", "benchmarking", "interviews", "data_modelling"],
    "presentation": ["insight_gen", "benchmarking", "data_modelling"],
    "workshops": ["insight_gen", "interviews"],
}

EXPECTED_UPSTREAM = 0.70
WORKSHOP_CASCADE_CAP = 0.80  # 80% of normal cascade boost


def compute_cascade_factor(module: str, completed_qualities: dict, case_modules: set) -> float:
    """Compute cascade quality factor from upstream modules.
    
    cascade = avg(upstream_qualities) / 0.70, capped [0.50, 1.15]
    Workshops get 80% capped boost.
    """
    deps = [d for d in DEPENDENCIES.get(module, []) if d in case_modules and d in completed_qualities]
    if not deps:
        return 1.0
    
    avg_upstream = sum(completed_qualities[d] for d in deps) / len(deps)
    normal_factor = max(0.50, min(1.15, avg_upstream / EXPECTED_UPSTREAM))
    
    if module == "workshops":
        return 1.0 + (normal_factor - 1.0) * WORKSHOP_CASCADE_CAP
    
    return normal_factor
