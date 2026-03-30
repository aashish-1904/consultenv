"""ConsultEnv FastAPI Server — OpenEnv HTTP API."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from models import ConsultAction, ConsultObservation, ConsultState
from server.environment import ConsultEnvironment

app = FastAPI(
    title="ConsultEnv",
    description="OpenEnv-compliant consulting engagement planning environment",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global environment instance
env = ConsultEnvironment()


class ResetRequest(BaseModel):
    scenario_id: str
    seed: Optional[int] = None


class StepRequest(BaseModel):
    action: ConsultAction


@app.get("/")
async def root():
    return {
        "name": "consultenv",
        "version": "1.0.0",
        "status": "running",
        "tasks": ["benchmarking_study", "cost_optimization", "ops_transformation", "commercial_due_diligence"],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/reset")
async def reset(request: ResetRequest) -> dict:
    try:
        obs = env.reset(scenario_id=request.scenario_id, seed=request.seed)
        return obs.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
async def step(request: StepRequest) -> dict:
    try:
        obs = env.step(request.action)
        return obs.model_dump()
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
async def state() -> dict:
    try:
        s = env.state()
        return s.model_dump()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
