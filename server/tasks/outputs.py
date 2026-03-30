"""Pre-computed output retrieval for modules."""

# Simplified output getter — returns placeholder outputs
# Full outputs are in scenario_outputs.py (42 entries)

def get_output(case_id, module, method="in_house", qc=False, int_count=None, sr_ratio=None):
    """Get pre-computed output for given parameters."""
    # Default output
    output = {
        "summary": f"Completed {module} for {case_id}",
        "details": f"Module {module} executed with method={method}, qc={qc}.",
        "data_points": {},
        "flags": [],
    }
    
    # Add discovery flags based on interview parameters
    if module == "interviews" and int_count and sr_ratio:
        n_senior = int(int_count * sr_ratio)
        output["summary"] = f"{int_count} interviews ({n_senior} senior, {int_count - n_senior} mid-level)"
        if n_senior >= 4:
            output["flags"].append("sufficient_senior_coverage")
    
    if module == "secondary" and qc:
        output["flags"].append("qc_validated")
    
    if module == "workshops":
        output["summary"] = "Workshop and implementation planning session completed"
    
    return output
