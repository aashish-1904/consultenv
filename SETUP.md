# ConsultEnv — Local Setup Guide

## Step 1: Extract

```bash
tar -xzf consultenv_project.tar.gz
cd consultenv
```

## Step 2: Sanity check (no deps needed)

```bash
python3 test_integration.py
# → 45 passed, 0 failed ✓
```

## Step 3: Docker build + run

```bash
docker build -t consultenv .
docker run -p 8000:8000 consultenv
```

Server starts at `http://localhost:8000`

## Step 4: Test API (new terminal)

```bash
# Health
curl http://localhost:8000/health

# Reset
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "benchmarking_study"}'

# Staff team
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"action_type": "staff_team", "parameters": {"associate": true}}}'

# Run all 4 modules
for mod in secondary benchmarking insight_gen presentation; do
  curl -s -X POST http://localhost:8000/step \
    -H "Content-Type: application/json" \
    -d "{\"action\": {\"action_type\": \"$mod\", \"parameters\": {}}}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  {d.get(\"latest_output\",{}).get(\"module\",\"?\")}:  q={d.get(\"latest_output\",{}).get(\"quality\",0):.3f}  done={d[\"done\"]}  reward={d[\"reward\"]:.3f}')"
done
```

## Step 5: Run all 4 scenarios (no Docker needed)

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from models import ConsultAction
from server.consultenv_environment import ConsultEnvEnvironment as ConsultEnvironment

env = ConsultEnvironment()
configs = {
    'benchmarking_study': (
        {'associate': True},
        [('secondary',{'data_source':'ibisworld'}),('benchmarking',{}),('insight_gen',{}),('presentation',{})]
    ),
    'cost_optimization': (
        {'assoc_consultant':True,'associate':True},
        [('secondary',{'data_source':'ibisworld'}),('interviews',{'interview_count':8,'senior_ratio':0.75,'qc':True}),
         ('benchmarking',{'qc':True}),('data_modelling',{'tool':'alteryx'}),
         ('insight_gen',{'insight_method':'ai_assisted'}),('presentation',{})]
    ),
    'ops_transformation': (
        {'assoc_consultant':True,'associate':True},
        [('secondary',{'data_source':'ibisworld'}),('interviews',{'interview_count':8,'senior_ratio':0.5,'qc':True}),
         ('benchmarking',{}),('data_modelling',{}),('insight_gen',{}),('presentation',{}),
         ('workshops',{'facilitator':'agile_coach','qc':True})]
    ),
    'commercial_due_diligence': (
        {'industry_expert':True,'consultant':True,'assoc_consultant':True,'associate':True},
        [('secondary',{'data_source':'bloomberg','qc':True}),('interviews',{'interview_count':8,'senior_ratio':0.5,'qc':True}),
         ('benchmarking',{}),('data_modelling',{}),('insight_gen',{}),('presentation',{}),
         ('workshops',{'facilitator':'agile_coach','qc':True})]
    ),
}
for sid,(team,mods) in configs.items():
    obs = env.reset(sid)
    env.step(ConsultAction(action_type='staff_team', parameters=team))
    for mod,p in mods:
        obs = env.step(ConsultAction(action_type=mod, parameters=p))
    print(f'{sid}: score={obs.total_reward:.3f}  margin={obs.resource_usage.margin:.1%}  days={obs.resource_usage.days_used:.1f}/{obs.resource_usage.days_total}  disc={obs.discovery_found}')
"
```

Expected:
```
benchmarking_study:          score=1.700  margin=46.2%  days=15.0/15  disc=False
cost_optimization:           score=1.878  margin=35.5%  days=24.1/25  disc=True
ops_transformation:          score=1.497  margin=25.3%  days=38.7/35  disc=False
commercial_due_diligence:    score=1.585  margin=14.0%  days=31.8/30  disc=True
```

## Step 6: Run LLM inference

```bash
# Set your API credentials
export API_BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-4o-mini
export HF_TOKEN=sk-your-key

# Install deps (if not using Docker)
pip install openai fastapi uvicorn pydantic

# Run
python inference.py
```

## Step 7: Deploy to HuggingFace Spaces

```bash
# 1. Create Space: huggingface.co → New Space → Docker SDK → tag "openenv"
# 2. Clone and push:
git clone https://huggingface.co/spaces/YOUR_USER/consultenv
cp -r consultenv/* .
git add . && git commit -m "Deploy" && git push
# 3. Verify:
curl https://YOUR_USER-consultenv.hf.space/health
```
