# main.py
import os
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from datetime import date
import logging
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from typing import TypedDict, Optional, List, Any, Dict
from CashFlow_Agents.agent import cashflow_agent
from Forecast_Agent.agent import run_forecasting_agent
from Risk_Anamoly_Agent.agent import run_risk_agent_async
from Collection_and_Intervention_Agent.agent import run_collections_workflow
from Liquidity_and_Collision_Detection_Agent.agent import CollisionAgent as collision_agent
from Scenario_Simulation_Agent.agent import scenario_agent
app = FastAPI()

logger = logging.getLogger(__name__)

# Read allowed origins from env (comma-separated). Fallback to sensible defaults.
_env_origins = os.getenv("ALLOWED_ORIGINS", "")
_allow_all = os.getenv("ALLOW_ALL_ORIGINS", "false").lower() in ("1", "true", "yes", "y")

if _allow_all:
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in _env_origins.split(",") if o.strip()]
    if not allowed_origins:
        allowed_origins = [
            "http://localhost",
            "http://localhost:4000",
            "http://127.0.0.1:4000",
            "https://fintro.nagarajneelam.me",
            "https://cfo-backend-883163069340.us-central1.run.app"
        ]

# If wildcard is used, browsers disallow credentials.
allow_credentials_flag = False if allowed_origins == ["*"] else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials_flag,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
class CashflowRequest(BaseModel):
    org_id: int
    period_start: date
    period_end: date


class CashflowResponse(BaseModel):
    org_id: int
    period_start: Optional[date]
    period_end: Optional[date]
    
    payments: List[Any]

    inflows: float
    outflows: float
    net_cashflow: float
    opening_balance: float
    closing_balance: float
    burn_rate: float
    risk_level: str

    explanation: str



@app.post("/cashflow", response_model=CashflowResponse)
def get_cashflow(req: CashflowRequest):
    result = cashflow_agent.invoke({
        "org_id": req.org_id,
        "period_start": req.period_start,
        "period_end": req.period_end,
    })

    return result

@app.get("/forecast")
async def get_forecast(org_id: int):
    """
    Run the Forecasting Agent for the given organization id.
    Example: GET /forecast?org_id=1
    """
    result = await run_forecasting_agent(org_id)
    return result


@app.get("/api/orgs/{org_id}/collisions")
async def get_collisions(org_id: int, backend_url: str | None = None):
 
    try:
        base = backend_url or os.getenv("API_BASE_URL", "https://fintro-backend-883163069340.asia-south1.run.app")
        agent = collision_agent(base)
        graph = await agent.create_graph()

        state = {
            "org_id": org_id,
            "current_step": "initialized"
        }

        result = await graph.ainvoke(state)
        return result.get("output", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/orgs/{org_id}/risk")
async def get_risk(org_id: int, backend_url: str | None = None):
    """
    Run Risk / Anomaly agent for the given organization id.
    Example: GET /api/orgs/12/risk
    """
    try:
        # If you want the Risk agent to use a different backend URL, set it via env or param.
        # Current Risk agent uses its own BASE_URL constant — adjust that file if you prefer env-config.
        result = await run_risk_agent_async(org_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/org/{org_id}/scenario", response_model=Dict[str, Any])
async def run_scenario_agent(org_id: int, payload: Dict[str, Any] = Body(...)):
    """
    Run the Scenario Analyzer (Agent 4).

    Expected JSON payload:
    {
      "scenario_instructions": ["delay collections by 15 days", "..."],
      "base_url": "https://fintro-backend-883163069340.asia-south1.run.app"   # optional, fallback inside agent defaults used if omitted
    }
    """
    scenario_instructions = payload.get("scenario_instructions", []) or []
    base_url = payload.get("base_url", "https://fintro-backend-883163069340.asia-south1.run.app")

    # Run the synchronous scenario_agent in a thread to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None, scenario_agent, org_id, scenario_instructions, base_url
        )
    except Exception as exc:
        # Preserve useful diagnostics for debugging
        raise HTTPException(status_code=500, detail=f"Scenario agent failed: {exc}")

    if not result or result.get("status") != "success":
        # If agent returns an error payload, propagate it with 400
        raise HTTPException(status_code=400, detail=result)

    return result

@app.post("/api/orgs/{org_id}/collections")
async def run_collections(org_id: int, payload: Dict[str, Any] = Body(...)):
    """
    Run Collections & Intervention workflow for an org.

    Request JSON (all fields optional; backend_url overrides API_BASE_URL env):
    {
      "base_url": "http://localhost:3000",
      "top_k_calls_today": 10
    }

    Response: the agent output (prioritized queue, full queue, drafts, metrics, etc.)
    """
    base_url = payload.get("base_url", os.getenv("API_BASE_URL", "https://fintro-backend-883163069340.asia-south1.run.app"))
    top_k = int(payload.get("top_k_calls_today", 10))

    try:
        # run the async orchestrator from the collections agent
        result = await run_collections_workflow(org_id, backend_url=base_url, top_k_calls_today=top_k)
    except Exception as exc:
        # preserve diagnostics useful for debugging
        raise HTTPException(status_code=500, detail=f"Collections workflow failed: {exc}")

    return result


# ...existing code...
from CFO_Orchestrator_Agent.agent import chat_with_cfo
# ...existing code...

@app.post("/chat")
async def cfo_chat(payload: Dict[str, Any] = Body(...)):
    """
    Simple chat endpoint:
    {
      "org_id": 123,
      "message": "Will we face a cash crunch in 30 days?",
      "base_url": "https://...optional..."
    }
    """
    org_id = int(payload.get("org_id"))
    message = str(payload.get("message", "")).strip()
    base_url = payload.get("base_url", None)
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    try:
        result = await chat_with_cfo(org_id, message, base_url=base_url)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat orchestration failed: {exc}")
