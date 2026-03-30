"""ConsultEnv Scenario Definitions — 4 Cases."""

SCENARIOS = {
    "benchmarking_study": {
        "id": "benchmarking_study",
        "name": "Benchmarking Study",
        "client": "HealthFirst (12 hospitals, $2B revenue)",
        "objective": "Benchmark procurement costs against industry peers and identify $20M+ in annual savings opportunities",
        "audience": "CFO and Chief Procurement Officer",
        "budget": 380250,
        "timeline_days": 15,
        "partner_days_wk": 2,
        "modules_required": ["secondary", "benchmarking", "insight_gen", "presentation"],
        "thresholds": {"secondary": 0.50, "benchmarking": 0.60, "insight_gen": 0.55, "presentation": 0.50},
        "workshop_base_override": None,
        "discovery_bonus": 0,
        "discovery_req": None,
        "discovery_description": None,
        "context": (
            "HealthFirst's procurement costs are reportedly 15% above industry average. "
            "The CFO wants hard numbers and a prioritized list of savings levers before "
            "the next board meeting. Speed and data accuracy are the priorities."
        ),
    },
    "cost_optimization": {
        "id": "cost_optimization",
        "name": "Cost Optimization",
        "client": "NovaChem Industries ($800M specialty chemicals)",
        "objective": "Identify $30M+ in operational cost reduction opportunities without impacting product quality or safety",
        "audience": "CEO, CFO, COO",
        "budget": 763750,
        "timeline_days": 25,
        "partner_days_wk": 3,
        "modules_required": ["secondary", "interviews", "benchmarking", "data_modelling", "insight_gen", "presentation"],
        "thresholds": {"secondary": 0.65, "benchmarking": 0.70, "interviews": 0.65, "data_modelling": 0.70, "insight_gen": 0.70, "presentation": 0.65},
        "workshop_base_override": None,
        "discovery_bonus": 0.10,
        "discovery_req": {"senior_interviews": 6},
        "discovery_description": "PE exit timeline: 36-month window, need 18% EBITDA by month 24",
        "context": (
            "NovaChem's EBITDA margins have declined from 18% to 13% over 3 years. "
            "PE ownership is pushing for a cost transformation. Previous cost-cutting attempt "
            "2 years ago failed — cuts were reversed within 6 months because they impacted "
            "production quality. The CFO is skeptical of typical consultant estimates."
        ),
    },
    "ops_transformation": {
        "id": "ops_transformation",
        "name": "Operational Transformation",
        "client": "TerraLogistics ($500M logistics company)",
        "objective": "Design and align stakeholders on a 12-month digital transformation roadmap targeting 20% operational efficiency gain",
        "audience": "CEO, CTO, 5 Department Heads",
        "budget": 1000000,
        "timeline_days": 35,
        "partner_days_wk": 3,
        "modules_required": ["secondary", "interviews", "benchmarking", "data_modelling", "insight_gen", "presentation", "workshops"],
        "thresholds": {"secondary": 0.65, "interviews": 0.70, "benchmarking": 0.70, "data_modelling": 0.70, "insight_gen": 0.75, "presentation": 0.70, "workshops": 0.90},
        "workshop_base_override": 11.25,
        "discovery_bonus": 0.15,
        "discovery_req": {"senior_interviews": 5},
        "discovery_description": "Hidden integration blocker: legacy ERP cannot interface with proposed cloud platform without $2M bridge",
        "context": (
            "TerraLogistics is under pressure to modernize its operations. Five department heads "
            "have competing priorities and the CEO needs a roadmap everyone can align on. "
            "The workshop IS the core deliverable — stakeholder buy-in is more important than "
            "the analysis itself. An agile coach is recommended for workshop facilitation."
        ),
    },
    "commercial_due_diligence": {
        "id": "commercial_due_diligence",
        "name": "Commercial Due Diligence",
        "client": "Meridian Capital Partners (PE fund, $2.4B AUM)",
        "objective": "Validate management case for AquaPure Technologies: $180M revenue, 25% market share, 15% CAGR, $50M EBITDA by Year 3",
        "audience": "Investment Committee (5 partners + deal team)",
        "budget": 1267500,
        "timeline_days": 30,
        "partner_days_wk": 4,
        "modules_required": ["secondary", "interviews", "benchmarking", "data_modelling", "insight_gen", "presentation", "workshops"],
        "thresholds": {"secondary": 0.75, "benchmarking": 0.80, "interviews": 0.80, "data_modelling": 0.80, "insight_gen": 0.80, "presentation": 0.80, "workshops": 0.95},
        "workshop_base_override": None,
        "discovery_bonus": 0.20,
        "discovery_req": {"senior_interviews": 4},
        "discovery_description": "Critical: #1 customer (18% of revenue) contract expiring in 6 months, actively evaluating competitors",
        "context": (
            "AquaPure is a leader in industrial water treatment. Management claims strong growth "
            "driven by tightening EPA regulations. Asking price is $320M (6.4x current EBITDA). "
            "Meridian needs to know: is the growth story real, are there hidden risks, and is "
            "the price right? Exclusivity expires in 5 weeks. Previous deal fell through due to "
            "missed risks in CDD. Both industry expert and agile coach are essential."
        ),
    },
}
