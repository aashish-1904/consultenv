"""Terminal (end-of-episode) reward computation."""


def compute_terminal_reward(
    module_qualities: dict,
    thresholds: dict,
    margin: float,
    days_used: float,
    timeline: int,
    discovery_found: bool,
    discovery_bonus: float,
    budget_exceeded: bool,
) -> dict:
    """Compute terminal reward at episode end.
    
    terminal = (quality × 0.15) + (profit × 0.45) + (timeline × 0.40) + discovery
    """
    # Count threshold failures
    below = sum(1 for mod, qual in module_qualities.items() 
                if mod in thresholds and qual < thresholds[mod])
    
    avg_quality = sum(module_qualities.values()) / len(module_qualities) if module_qualities else 0
    
    # Quality score
    if below >= 2:
        quality_score = 0.0
    elif below == 1:
        quality_score = avg_quality / 2
    else:
        quality_score = avg_quality
    
    # Profit score
    if margin > 0.35: profit_score = 1.0
    elif margin > 0.30: profit_score = 0.85
    elif margin > 0.25: profit_score = 0.70
    elif margin > 0.20: profit_score = 0.45
    elif margin > 0.15: profit_score = 0.20
    elif margin > 0.10: profit_score = 0.05
    else: profit_score = 0.0
    
    # Timeline score + overrun penalties
    overrun = max(0, days_used - timeline)
    if overrun == 0:
        timeline_score = 1.0 if days_used / timeline <= 0.9 else 0.85
        timeline_penalty = 0.0
    elif overrun < 3:
        timeline_score = 0.30
        timeline_penalty = -0.2
    elif overrun <= 5:
        timeline_score = 0.10
        timeline_penalty = -0.5
    else:
        timeline_score = 0.0
        timeline_penalty = -1.0
    
    # Discovery
    disc = discovery_bonus if discovery_found else 0.0
    
    # Terminal
    terminal = (quality_score * 0.15) + (profit_score * 0.45) + (timeline_score * 0.40) + disc + timeline_penalty

    # Threshold failure escalation: quality zeroing alone isn't enough to
    # prevent "cheap garbage" strategies from scoring well on profit/timeline
    if below >= 2:
        terminal += -0.10 * below
    elif below == 1:
        terminal += -0.05

    # Budget nuclear — goes NEGATIVE, not just zero
    if budget_exceeded:
        terminal = -0.5
    
    return {
        "terminal_reward": round(terminal, 4),
        "quality_score": round(quality_score, 4),
        "profit_score": round(profit_score, 4),
        "timeline_score": round(timeline_score, 4),
        "timeline_penalty": timeline_penalty,
        "discovery_bonus": disc,
        "modules_below_threshold": below,
        "avg_quality": round(avg_quality, 4),
        "margin": round(margin, 4),
        "days_overrun": round(overrun, 2),
        "budget_exceeded": budget_exceeded,
    }
