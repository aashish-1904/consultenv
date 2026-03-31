"""FastAPI application for the ConsultEnv Environment."""

import json

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv is required. Install with: pip install openenv-core[core]>=0.2.2"
    ) from e

try:
    from ..models import ConsultAction, ConsultObservation
    from .consultenv_environment import ConsultEnvEnvironment
except (ImportError, ModuleNotFoundError):
    from models import ConsultAction, ConsultObservation
    from server.consultenv_environment import ConsultEnvEnvironment


app = create_app(
    ConsultEnvEnvironment,
    ConsultAction,
    ConsultObservation,
    env_name="consultenv",
    max_concurrent_envs=1,
)

# Override /reset to handle empty body (the validator sends POST /reset with no body)
from fastapi import Request, HTTPException

# Remove the existing /reset route that create_app added
app.routes[:] = [r for r in app.routes if not (hasattr(r, 'path') and r.path == '/reset' and hasattr(r, 'methods') and 'POST' in r.methods)]

_env_instance = ConsultEnvEnvironment()

@app.post("/reset")
async def reset_override(request: Request):
    try:
        body_bytes = await request.body()
        body = json.loads(body_bytes) if body_bytes and body_bytes.strip() else {}
    except Exception:
        body = {}
    try:
        scenario_id = body.get("scenario_id") or body.get("task_id") or None
        seed = body.get("seed")
        obs = _env_instance.reset(scenario_id=scenario_id, seed=seed)
        return obs.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/reset")
async def reset_get():
    try:
        obs = _env_instance.reset()
        return obs.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Also override /step to use the same instance
@app.post("/step")
async def step_override(request: Request):
    try:
        body_bytes = await request.body()
        body = json.loads(body_bytes) if body_bytes and body_bytes.strip() else {}
    except Exception:
        raise HTTPException(status_code=400, detail="Request body required for /step")
    try:
        action_data = body.get("action", body)
        action = ConsultAction(
            action_type=action_data.get("action_type", ""),
            parameters=action_data.get("parameters", {}),
        )
        obs = _env_instance.step(action)
        return obs.model_dump()
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/state")
async def state_override():
    try:
        s = _env_instance.get_consult_state()
        return s.model_dump() if hasattr(s, 'model_dump') else s.__dict__
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()