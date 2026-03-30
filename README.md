# ConsultEnv — Consulting Engagement Planning Environment

An OpenEnv-compliant reinforcement learning environment that simulates end-to-end consulting engagement management. An AI agent staffs teams, selects methodologies and tools, manages budgets and timelines, and delivers client work — with every decision producing deterministic outcomes scored on quality, profitability, and timeliness.

---

## Why This Environment?

### What does this simulate?

Consulting engagement management — the process of planning, resourcing, and executing a client project from kickoff to final deliverable. This is a genuine task performed daily by thousands of firms (McKinsey, BCG, Bain, Deloitte, Accenture, and every boutique in between). A typical engagement involves:

- **Team staffing**: Who do we put on this project? Specialists are expensive but boost quality.
- **Methodology selection**: Do we use in-house research or buy Bloomberg data? Manual analysis or AI tools?
- **Budget management**: Every hire, tool license, and external vendor eats into the profit margin.
- **Timeline management**: Client has a hard deadline. Overrun = lost credibility (and lost fees).
- **Quality delivery**: Each deliverable module must meet a quality threshold or the whole engagement fails.

### Why is this valuable for agent evaluation?

Real consulting engagement planning requires:

- **Multi-step reasoning**: 5-8 sequential decisions with dependencies between them
- **Resource optimization under constraints**: Balance quality vs. cost vs. speed simultaneously
- **Strategic traps**: Cheap AI tools look appealing but destroy quality; Bloomberg data is premium but expensive
- **Hidden information**: Discovery mechanics reward agents that invest in deep investigation
- **Cascading consequences**: One bad early decision ripples through the entire project

Firms are actively exploring AI for project planning and resource optimization. An agent that masters ConsultEnv would provide genuine commercial value.

### Domain mechanics at a glance

| Mechanic | What it models | Agent challenge |
|----------|---------------|-----------------|
| Team staffing | Resource allocation | Hire the right specialists without overspending |
| Module sequencing | Project planning | Execute work in logical dependency order |
| Tool/method selection | Methodology choice | Navigate cost/quality/speed tradeoffs |
| QC toggle | Quality assurance | Invest time in QC on weak modules, skip on strong ones |
| Cascading quality | Compounding errors | Early mistakes destroy downstream deliverables |
| Workshop isolation | Facilitation expertise | Only specialists can deliver high-quality workshops |
| Discovery mechanics | Due diligence depth | Senior interviews unlock hidden findings worth bonus points |
| Budget nuclear | Financial discipline | Exceed the budget = entire terminal reward zeroed |
| Timeline penalties | Deadline management | Overruns incur steep negative penalties |

---

## Tasks & Difficulty Progression

### 4 Tasks with Genuine Difficulty Progression

| Task | Client | Budget | Timeline | Modules | Difficulty | Pass Rate | Key Challenge |
|------|--------|--------|----------|---------|------------|-----------|---------------|
| **Benchmarking Study** | HealthFirst (12 hospitals, $2B) | $380,250 | 15 days | 4 | Easy (3/10) | 10/12 | Data source selection |
| **Cost Optimization** | NovaChem ($800M chemicals) | $763,750 | 25 days | 6 | Medium (5/10) | 7/10 | Tool stack + discovery |
| **Ops Transformation** | TerraLogistics ($500M logistics) | $1,000,000 | 35 days | 7 | Hard (8/10) | 1/11 | Workshop facilitation |
| **Commercial Due Diligence** | Meridian Capital (PE fund) | $1,267,500 | 30 days | 7 | Expert (9/10) | 2/9 | Expert + Coach + tight margins |

### What makes each task harder?

**Easy — Benchmarking Study**: HealthFirst's procurement costs are reportedly 15% above industry average. The CFO wants hard numbers and a prioritized list of savings levers before the next board meeting. Speed and data accuracy are the priorities.

**Medium — Cost Optimization**: NovaChem's EBITDA margins have declined from 18% to 13% over 3 years. PE ownership is pushing for a cost transformation. A previous cost-cutting attempt failed — cuts were reversed within 6 months because they impacted production quality.

**Hard — Ops Transformation**: TerraLogistics is under pressure to modernize its operations. Five department heads have competing priorities and the CEO needs a roadmap everyone can align on. Stakeholder buy-in through workshops is more important than the analysis itself.

**Expert — Commercial Due Diligence**: Meridian Capital needs to validate the management case for AquaPure Technologies ($180M revenue, 25% market share). Asking price is $320M at 6.4x EBITDA. Exclusivity expires in 5 weeks and a previous deal fell through due to missed risks in CDD.


### Stress testing

Each case was tested against 10-12 distinct strategies covering optimal plays, common mistakes, budget traps, wrong ordering, missing specialists, and degenerate strategies (Partner + Manager only). The results show meaningful differentiation between agent capabilities.

---

## How It Works

### OpenEnv API

```
reset(scenario_id)  →  ConsultObservation  (initial state, scenario brief)
step(action)        →  ConsultObservation  (updated state, reward, module output)  
state()             →  ConsultState        (internal state for debugging)
```

### Action Space

**Staff Team** (must be first action):
```json
{
  "action_type": "staff_team",
  "parameters": {
    "consultant": true,
    "assoc_consultant": true,
    "associate": true,
    "offshore_analyst": false,
    "industry_expert": false
  }
}
```

**Module Execution** (7 module types, each with unique parameters):
```json
{"action_type": "secondary",      "parameters": {"method": "in_house", "data_source": "ibisworld", "qc": false}}
{"action_type": "interviews",     "parameters": {"interview_count": 8, "senior_ratio": 0.75, "qc": true}}
{"action_type": "benchmarking",   "parameters": {"method": "vendor", "qc": true}}
{"action_type": "data_modelling", "parameters": {"tool": "alteryx", "qc": false}}
{"action_type": "insight_gen",    "parameters": {"insight_method": "ai_assisted", "qc": false}}
{"action_type": "presentation",   "parameters": {"pres_method": "graphics", "qc": false}}
{"action_type": "workshops",      "parameters": {"facilitator": "agile_coach", "qc": true}}
```

Parameter options per module:

| Module | Parameters | Options |
|--------|-----------|---------|
| Secondary Research | method × data_source × qc | 3 methods × 7 data sources × 2 QC = 42 combos |
| Benchmarking | method × qc | 3 × 2 = 6 |
| Interviews | count × senior_ratio × qc | 8 counts × continuous ratio × 2 = many |
| Data Modelling | tool × qc | 3 × 2 = 6 (copilot is a trap) |
| Insight Generation | method × qc | 3 × 2 = 6 (junior_ai_deep unlocks discovery shortcut) |
| Presentation | method × qc | 3 × 2 = 6 (ai_generated is a quality trap) |
| Workshop | facilitator × qc | 3 × 2 = 6 (isolated module — only specialist quality) |

### Observation Space

The agent receives a rich observation after each step:

```python
ConsultObservation(
    scenario: ScenarioSpec        # Client brief, budget, timeline, thresholds, context
    available_actions: list       # What actions can be taken next
    available_roles: list         # Team role descriptions, costs, specialties
    available_modules: list       # Module descriptions and base properties
    step_index: int               # Current step number
    team: TeamComposition         # Current team roles, weekly cost, total cost
    pipeline_history: list        # All prior steps with outputs and reward breakdowns
    resource_usage: ResourceUsage # Budget spent/remaining, days used/remaining, margin
    latest_output: ModuleOutput   # Quality score, threshold, pass/fail, text summary
    key_findings: list            # Accumulated discoveries and warning flags
    discovery_found: bool         # Whether hidden finding was unlocked
    done: bool                    # Episode complete?
    reward: float                 # This step's reward
    total_reward: float           # Cumulative episode score
)
```

### Reward Function — Non-Sparse, Multi-Dimensional

**Per-Step Reward** (every action gets scored):
```
step_reward = (sequencing × 0.35) + (quality × 0.40) + (efficiency × 0.25) + penalties
```

| Component | Weight | What it measures |
|-----------|--------|-----------------|
| Sequencing | 35% | Is this module in the correct position? Are dependencies met? |
| Quality | 40% | Module quality after team boosts, cascade, and QC |
| Efficiency | 25% | Budget/time burn rate proportional to progress |
| Dep violation | -0.2 | Executing a module before its dependencies |
| Threshold fail | -0.1 | Module quality below case threshold |

**Terminal Reward** (end of episode):
```
terminal = (quality × 0.45) + (profit × 0.35) + (timeline × 0.20) + discovery_bonus + timeline_penalty
```

| Component | Weight | Scoring |
|-----------|--------|---------|
| Quality | 45% | Avg quality. 1 fail = halved. 2+ fails = zeroed. |
| Profit | 35% | Margin >35% = 1.0, 25-30% = 0.70, <10% = 0.0 |
| Timeline | 20% | On time ≤90% = 1.0, on time 100% = 0.85, overrun = 0.30 |
| Discovery | +0.10 to +0.20 | Bonus for unlocking hidden findings |

**Penalty escalation** (overruns hurt — a lot):

| Condition | Timeline Score | Penalty |
|-----------|---------------|---------|
| On time (≤90% used) | 1.0 | 0.0 |
| On time (90-100% used) | 0.85 | 0.0 |
| 0-3 days overrun | 0.30 | **-0.2** |
| 3-5 days overrun | 0.10 | **-0.5** |
| >5 days overrun | 0.00 | **-1.0** |
| Budget exceeded | — | **terminal = -0.5** |

**Total Episode Score:**
```
total = average(per_step_rewards) + terminal_reward
```

### Key Mechanics

**Cascading Quality**: Upstream module quality affects downstream modules via cascade factor (avg upstream / 0.70, capped 0.50 to 1.15). One weak early module tanks the entire engagement.

**Workshop Isolation**: No team speed or quality multipliers apply to workshops. Only Industry Expert specialist (+0.30) or Agile Coach parameter (+0.25) affect workshop quality. Workshop cascade is capped at 80% of normal.

**Dynamic QC**: Quality boost varies with pre-QC quality — bigger boost on weaker outputs (+0.20 at ≤0.50, only +0.03 at >0.90). Rewards strategic QC placement.

**Discovery**: Hidden findings unlock when agent conducts enough senior interviews. The `junior_ai_deep` insight method lowers the threshold by 2, creating an alternative discovery path.

**Team Roles — Single Specialty**: Each optional role has one speed specialty module and one quality specialty module. Hiring decisions require understanding which roles benefit which modules.

| Role | Rate/Day | Speed Specialist | Quality Specialist |
|------|----------|-----------------|-------------------|
| Consultant | $5,000 | insight_gen (-20%) | presentation (+0.20) |
| Assoc Consultant | $3,500 | interviews (-20%) | insight_gen (+0.20) |
| Associate | $2,500 | secondary (-20%) | benchmarking (+0.20) |
| Offshore Analyst | $1,500 | data_modelling (-25%) | data_modelling (+0.15) |
| Industry Expert | $8,000 | — | workshops (+0.30) |

**Agile Coach** is not a team role — it's a workshop facilitator hired per-day ($6,500/day × actual workshop days). Gives +0.25 quality and 15% speed boost to workshops only.

---

## Setup & Architecture

### OpenEnv Compliance

| Requirement | Status |
|------------|--------|
| `openenv.yaml` with task definitions | ✅ 4 tasks with IDs, descriptions, difficulty |
| Typed Pydantic models | ✅ ConsultAction, ConsultObservation, ConsultState |
| `reset()` → clean state | ✅ Full state reset on each call |
| `step(action)` → observation + reward | ✅ Returns typed observation with reward breakdown |
| `state()` → internal state | ✅ Full serializable state |
| FastAPI HTTP endpoints | ✅ POST /reset, POST /step, GET /state, GET /health |
| Dockerfile | ✅ python:3.11-slim, port 7860 |
| `inference.py` in root | ✅ OpenAI client, env vars, fallback heuristics |
| Deterministic grading | ✅ Same inputs = same outputs, always |
| 0.0-1.0 grader range | ✅ Per-step and terminal scores bounded (terminal can go negative as penalty) |

### Testing

- **45 integration tests** covering team costs, speed/quality multipliers, workshop isolation, cascade factors, module execution, sequencing, full episodes for all 4 cases, budget nuclear, wrong ordering, QC cascade effects, and discovery mechanics.
- **All 45 pass** consistently.

### Project Structure

```
consultenv/
├── openenv.yaml              # OpenEnv metadata — 4 tasks
├── inference.py              # Baseline inference script (OpenAI client)
├── demo_run.py               # Demo runner (no LLM needed)
├── test_integration.py       # 45 integration tests
├── Dockerfile                # HF Spaces deployment
├── README.md                 # This file
├── requirements.txt          # fastapi, uvicorn, pydantic, openai
├── models.py                 # Typed models (works with or without pydantic)
├── server/
│   ├── app.py                # FastAPI server (port 7860)
│   ├── environment.py        # Main environment class
│   ├── simulator/
│   │   ├── transition.py     # Module execution engine (all parameters)
│   │   ├── team.py           # Team multiplier calculations
│   │   └── cascade.py        # Cascading quality + 80% workshop cap
│   ├── rewards/
│   │   ├── step_reward.py    # Per-step reward (seq + quality + efficiency)
│   │   └── terminal_reward.py # Terminal reward (quality + profit + timeline + penalties)
│   ├── rules/
│   │   └── sequencing.py     # Ideal order validation + dependency checks
│   └── tasks/
│       ├── scenarios.py      # 4 scenario definitions with full config
│       └── outputs.py        # Pre-computed text outputs
```

### Inference Script

`inference.py` follows the hackathon spec exactly:

- Uses **OpenAI client** for all LLM calls
- Reads **`API_BASE_URL`**, **`MODEL_NAME`**, **`HF_TOKEN`** from environment variables
- Loops through all 4 tasks and prints per-task and average scores
- Includes **fallback heuristics** when LLM fails (parses errors, retries with safe defaults)
- Completes within time/resource limits

### Running

```bash
# No LLM needed — demo with hardcoded optimal strategies
python demo_run.py

# Run specific case
python demo_run.py benchmarking_study

# Start HTTP server
python server/app.py

# Run demo via HTTP API
python demo_run.py --http

# Run with LLM inference
export API_BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-3.5-turbo
export HF_TOKEN=your_key
python inference.py

# Run integration tests
python test_integration.py
```

---

## Novel Mechanics


| Mechanic | Description | Why it matters |
|----------|------------|----------------|
| **Cascading quality** | Upstream module quality multiplies downstream quality via dependency graph | One bad early decision compounds through the entire engagement |
| **Workshop isolation** | No team multipliers on workshops — only specialist facilitators | Agent can't "cheese" workshop quality with team composition |
| **80% workshop cascade cap** | Workshop gets reduced benefit from upstream quality | Forces direct investment in workshop expertise |
| **Agile Coach as per-day hire** | Workshop-only facilitator paid per actual workshop day, not per engagement | Creates a genuine cost optimization decision |
| **Expert + Coach synergy** | Hardest case requires BOTH specialists together for workshop threshold | Agent must discover non-obvious combination |
| **Triple tension** | Quality vs. profit vs. speed must be balanced simultaneously | No single optimization axis works |
| **Tool traps** | Copilot AI and AI-generated presentations look cheap but destroy quality | Tests whether agent reads specs carefully |
| **Discovery breakpoints** | Senior interview count unlocks hidden findings worth terminal bonus | Rewards deep investigation over surface-level work |
| **junior_ai_deep shortcut** | AI analysis method lowers discovery threshold by 2 interviews | Creates alternative discovery path — fewer interviews + AI |
| **Budget nuclear with negative terminal** | Exceeding budget sets terminal to -0.5 (not zero) | Total episode score can be negative — strong aversive signal |
| **Steep timeline penalties** | Even 0.1 day overrun triggers -0.2 penalty; >5 days = -1.0 | Agent must actively manage time, not just quality |
| **Dynamic QC boost** | QC gives bigger boost to weaker modules, diminishing returns on strong ones | Rewards strategic QC placement |
| **Single-specialty roles** | Each team member has exactly one speed and one quality specialist module | No generalist team composition — targeted hiring matters |


---

