"""Team composition and multiplier calculations."""

ROLES = {
    "Partner":          {"rate":10000,"speed_overall":0,"speed_spec_mod":None,"speed_spec_val":0,"qual_overall":0,"qual_spec_mod":None,"qual_spec_val":0},
    "Manager":          {"rate":7000,"speed_overall":0,"speed_spec_mod":None,"speed_spec_val":0,"qual_overall":0,"qual_spec_mod":None,"qual_spec_val":0},
    "Consultant":       {"rate":5000,"speed_overall":-0.05,"speed_spec_mod":"insight_gen","speed_spec_val":-0.20,"qual_overall":0.04,"qual_spec_mod":"presentation","qual_spec_val":0.20},
    "Assoc Consultant": {"rate":3500,"speed_overall":-0.05,"speed_spec_mod":"interviews","speed_spec_val":-0.20,"qual_overall":0.04,"qual_spec_mod":"insight_gen","qual_spec_val":0.20},
    "Associate":        {"rate":2500,"speed_overall":-0.05,"speed_spec_mod":"secondary","speed_spec_val":-0.20,"qual_overall":0.04,"qual_spec_mod":"benchmarking","qual_spec_val":0.20},
    "Offshore Analyst": {"rate":1500,"speed_overall":-0.02,"speed_spec_mod":"data_modelling","speed_spec_val":-0.25,"qual_overall":0.00,"qual_spec_mod":"data_modelling","qual_spec_val":0.15},
    "Industry Expert":  {"rate":8000,"speed_overall":-0.01,"speed_spec_mod":None,"speed_spec_val":0,"qual_overall":0.03,"qual_spec_mod":"workshops","qual_spec_val":0.30},
}

OPTIONAL_ROLES = ["Consultant", "Assoc Consultant", "Associate", "Offshore Analyst", "Industry Expert"]


def compute_team_cost(roles: list, partner_days_wk: int, timeline_days: int) -> tuple:
    """Returns (weekly_cost, total_cost)."""
    weeks = -(-timeline_days // 5)
    weekly = 0
    for role in roles:
        r = ROLES[role]
        dw = partner_days_wk if role == "Partner" else 5
        weekly += r["rate"] * dw
    return weekly, weekly * weeks


def compute_speed_multiplier(module: str, optional_roles: list) -> float:
    """Compute speed multiplier for a module from team composition.
    Workshops are ISOLATED — returns 1.0 (no team speed)."""
    if module == "workshops":
        return 1.0
    mult = 1.0
    for role in optional_roles:
        r = ROLES[role]
        if r["speed_spec_mod"] == module:
            mult += r["speed_spec_val"]
        else:
            mult += r["speed_overall"]
    return max(mult, 0.30)


def compute_quality_boost(module: str, optional_roles: list) -> float:
    """Compute quality boost for a module from team composition.
    Workshops are ISOLATED — only Expert specialist applies."""
    if module == "workshops":
        for role in optional_roles:
            r = ROLES[role]
            if r["qual_spec_mod"] == "workshops":
                return r["qual_spec_val"]
        return 0.0

    boost = 0.0
    for role in optional_roles:
        r = ROLES[role]
        if r["qual_spec_mod"] == module:
            boost += r["qual_spec_val"]
        else:
            boost += r["qual_overall"]
    return boost


def get_role_infos():
    """Return role info list for observation."""
    from models import RoleInfo
    infos = []
    for name, r in ROLES.items():
        if name in ("Partner", "Manager"):
            continue
        desc_parts = [f"${r['rate']:,}/day"]
        if r["speed_spec_mod"]:
            desc_parts.append(f"Speed specialist: {r['speed_spec_mod']} ({r['speed_spec_val']:+.0%})")
        if r["qual_spec_mod"]:
            desc_parts.append(f"Quality specialist: {r['qual_spec_mod']} ({r['qual_spec_val']:+.0%})")
        infos.append(RoleInfo(
            name=name,
            billing_rate=r["rate"],
            speed_overall=r["speed_overall"],
            speed_specialty=r["speed_spec_mod"],
            speed_specialty_value=r["speed_spec_val"],
            quality_overall=r["qual_overall"],
            quality_specialty=r["qual_spec_mod"],
            quality_specialty_value=r["qual_spec_val"],
            description=". ".join(desc_parts),
        ))
    return infos
