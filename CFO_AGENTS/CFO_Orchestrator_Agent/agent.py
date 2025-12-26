import os
import asyncio
import json
import re
import logging
import time
from typing import Dict, Any, Optional, List

from langchain_google_genai import ChatGoogleGenerativeAI

from Forecast_Agent.agent import run_forecasting_agent
from Risk_Anamoly_Agent.agent import run_risk_agent_async
from Collection_and_Intervention_Agent.agent import run_collections_workflow
from Liquidity_and_Collision_Detection_Agent.agent import CollisionAgent
from CashFlow_Agents.agent import cashflow_agent
from Scenario_Simulation_Agent.agent import scenario_agent

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY is not set")

LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")
API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://fintro-backend-883163069340.asia-south1.run.app"
)

AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "12"))  # seconds
ALLOWED_AGENTS = {
    "cashflow",
    "forecast",
    "risk",
    "collections",
    "collisions",
    "scenario"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cfo-copilot")

# -------------------------------------------------------------------
# LLM (langchain/google-genai Chat model)
# -------------------------------------------------------------------

_llm = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    temperature=0.2,
    api_key=GOOGLE_API_KEY
)

# -------------------------------------------------------------------
# Collision graph cache (langgraph) keyed by base_url
# -------------------------------------------------------------------

_collision_graphs: Dict[str, Any] = {}


async def get_collision_graph(base: Optional[str] = None):
    """
    Return a cached collision graph for a given base URL.
    If no graph exists for the base, construct one and cache it.
    """
    base = (base or API_BASE_URL).rstrip("/")
    global _collision_graphs
    if base in _collision_graphs and _collision_graphs[base] is not None:
        return _collision_graphs[base]

    logger.info("Initializing Collision LangGraph for base=%s", base)
    coll = CollisionAgent(base)
    graph = await coll.create_graph()
    _collision_graphs[base] = graph
    return graph


# -------------------------------------------------------------------
# SAFE HELPERS
# -------------------------------------------------------------------

def safe_result(val):
    return {} if isinstance(val, Exception) else (val or {})


def extract_json(text: str) -> Dict[str, Any]:
    """
    Robustly extract JSON from LLM output.
    Steps:
      1) Try json.loads(text)
      2) Try fenced code block like ```json\n{...}\n``` or ```\n{...}\n```
      3) Try the first {...} .. last } substring
      4) Fallback to returning {"reply": text}
    """
    if not text:
        return {"reply": ""}

    # 1) direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) fenced code block capture (```json {...} ``` or ``` {...} ```)
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S | re.I)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # 3) first {...} to last } block as a fallback
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 4) final fallback
    return {"reply": text.strip()}


def validate_actions(actions: Optional[List[Dict[str, Any]]]) -> List[Dict[str, str]]:
    """
    Ensure LLM only requests allowed agents and sanitize entries.
    Normalizes agent names to lowercase and returns list of dicts:
      {"agent": "<agent>", "action": "<action text>"}
    """
    valid: List[Dict[str, str]] = []
    if not actions:
        return valid

    for a in actions:
        if not isinstance(a, dict):
            continue
        agent_name = str(a.get("agent", "") or "").strip().lower()
        action_text = str(a.get("action", "") or "").strip()
        if agent_name in ALLOWED_AGENTS and action_text:
            valid.append({"agent": agent_name, "action": action_text})
    return valid


# -------------------------------------------------------------------
# AGENT RUNNER
# -------------------------------------------------------------------

async def run_agent_by_name(org_id: int, agent_name: str, base_url: Optional[str] = None) -> Any:
    """
    Generic helper to call any supported agent by name.
    Returns the raw agent output (or an Exception will be returned by caller).
    """
    base = (base_url or API_BASE_URL).rstrip("/")
    agent_name = agent_name.strip().lower()

    if agent_name == "forecast":
        return await run_forecasting_agent(org_id)
    if agent_name == "risk":
        return await run_risk_agent_async(org_id)
    if agent_name == "collections":
        # collections workflow accepts backend_url param
        return await run_collections_workflow(org_id, backend_url=base)
    if agent_name == "collisions":
        coll_graph = await get_collision_graph(base)
        return await coll_graph.ainvoke({"org_id": org_id, "current_step": "initialized"})
    if agent_name == "cashflow":
        # cashflow agent is synchronous — run in thread
        return await asyncio.to_thread(cashflow_agent.invoke, {"org_id": org_id, "period_start": None, "period_end": None})
    if agent_name == "scenario":
        # scenario_agent is sync in many implementations — run in thread
        return await asyncio.to_thread(scenario_agent, org_id, [], base)
    raise ValueError(f"Unknown agent: {agent_name}")


# -------------------------------------------------------------------
# AGENT ORCHESTRATION (gather)
# -------------------------------------------------------------------

async def gather_agents(org_id: int, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Concurrently fetch outputs from the core agents. This function applies
    timeouts and normalizes results (exceptions => empty dict). It also logs
    compact diagnostics for each agent result to help debug missing data.
    """
    start_ts = time.time()
    base = (base_url or API_BASE_URL).rstrip("/")

    async def with_timeout(coro, name: str):
        try:
            return await asyncio.wait_for(coro, timeout=AGENT_TIMEOUT)
        except asyncio.TimeoutError as te:
            logger.warning("Agent '%s' call timed out: %s", name, te)
            return te
        except Exception as e:
            logger.exception("Agent '%s' call raised: %s", name, e)
            return e

    # Kick off concurrent calls and capture exceptions
    gathered = await asyncio.gather(
        with_timeout(run_agent_by_name(org_id, "forecast", base), "forecast"),
        with_timeout(run_agent_by_name(org_id, "risk", base), "risk"),
        with_timeout(run_agent_by_name(org_id, "collections", base), "collections"),
        with_timeout(run_agent_by_name(org_id, "collisions", base), "collisions"),
        with_timeout(run_agent_by_name(org_id, "cashflow", base), "cashflow"),
        return_exceptions=True
    )

    # Map each to safe_result and add debug logs describing shapes
    names = ["forecast", "risk", "collections", "collisions", "cashflow"]
    results = {}
    for name, raw in zip(names, gathered):
        normalized = safe_result(raw)
        # If langgraph nodes returned {"output": {...}} unwrap for logging/inspection
        if isinstance(normalized, dict) and "output" in normalized and isinstance(normalized.get("output"), dict):
            sample = normalized.get("output")
        else:
            sample = normalized

        # Log a compact summary to help debug missing data
        try:
            if isinstance(sample, dict):
                keys = list(sample.keys())
                # Prefer showing summary info if present
                if "summary" in sample and isinstance(sample["summary"], dict):
                    summary = sample["summary"]
                    logger.info("Agent '%s' => dict keys=%s; summary_keys=%s", name, keys[:8], list(summary.keys()))
                else:
                    logger.info("Agent '%s' => dict keys=%s", name, keys[:8])
            elif isinstance(sample, list):
                logger.info("Agent '%s' => list len=%s (first item keys=%s)", name, len(sample), (list(sample[0].keys())[:5] if sample else None))
            elif isinstance(sample, Exception):
                logger.warning("Agent '%s' => exception: %s", name, repr(sample))
            else:
                logger.info("Agent '%s' => type=%s repr=%s", name, type(sample).__name__, str(sample)[:200])
        except Exception:
            logger.exception("Failed logging summary for agent %s", name)

        # store normalized output (unwrap output if necessary)
        if isinstance(normalized, dict) and "output" in normalized and isinstance(normalized.get("output"), dict):
            results[name] = normalized.get("output") or {}
        else:
            results[name] = normalized or {}

    elapsed = time.time() - start_ts
    logger.info("gather_agents completed in %.2fs", elapsed)
    return results


# -------------------------------------------------------------------
# PROMPT / LLM
# -------------------------------------------------------------------

def build_prompt(user_message: str, org_id: int, ctx: Dict[str, Any]) -> str:
    f = ctx.get("forecast", {}).get("summary", {})
    r = ctx.get("risk", {}).get("customer_risk_scores", [])[:3]
    c = ctx.get("collections", {}).get("prioritized_queue", [])[:5]
    cf = ctx.get("cashflow", {})
    collisions = ctx.get("collisions", {}).get("collision_list", []) if isinstance(ctx.get("collisions", {}), dict) else []

    return f"""
You are Fintro's Autonomous CFO Copilot.

Organization ID: {org_id}

User Question:
\"\"\"{user_message}\"\"\"

System Context (from internal agents):
- Forecast: min_balance={f.get("min_balance")} current_balance={f.get("current_balance")}
- Top Risk Customers: {r}
- Top Collections Queue: {c}
- Cashflow: opening={cf.get("opening_balance")} closing={cf.get("closing_balance")}
- Upcoming Liquidity Collisions: {len(collisions)}

Instructions:
1. Answer concisely (2–4 short paragraphs).
2. Recommend at most 5 concrete actions.
3. Each action must reference one of these agents:
   cashflow, forecast, risk, collections, collisions, scenario
4. Optionally suggest ONE scenario to simulate.

Return STRICT JSON:
{{
  "reply": "string",
  "actions": [{{"agent": "agent_name", "action": "what to do"}}],
  "suggested_scenario": "optional string"
}}
"""


# -------------------------------------------------------------------
# MAIN ENTRY
# -------------------------------------------------------------------

async def chat_with_cfo(
    org_id: int,
    user_message: str,
    base_url: Optional[str] = None,
    execute_actions: bool = False
) -> Dict[str, Any]:
    """
    Orchestrate agent calls, call the LLM and parse its structured response.

    - If `execute_actions` is True, validated actions will be executed via `run_agent_by_name`
      (use with caution — actions are executed synchronously/async as implemented).
    """
    logger.info("Starting chat orchestration for org_id=%s", org_id)
    ctx = await gather_agents(org_id, base_url)
    prompt = build_prompt(user_message, org_id, ctx)

    # call LLM in thread (model's invoke is blocking in many implementations)
    llm_resp = await asyncio.to_thread(_llm.invoke, prompt)
    raw_text = getattr(llm_resp, "content", str(llm_resp))
    logger.debug("LLM raw: %s", raw_text[:1000])

    structured = extract_json(raw_text)
    if not isinstance(structured, dict):
        structured = {"reply": str(structured)}

    # Guarantee actions field exists and validate/normalize it
    raw_actions = structured.get("actions", []) if isinstance(structured, dict) else []
    validated_actions = validate_actions(raw_actions)
    structured["actions"] = validated_actions

    # Optionally execute validated actions (disabled by default)
    executed_results = []
    if execute_actions and validated_actions:
        for act in validated_actions:
            try:
                res = await asyncio.wait_for(run_agent_by_name(org_id, act["agent"], base_url), timeout=AGENT_TIMEOUT)
                executed_results.append({"action": act, "result": safe_result(res)})
            except Exception as ex:
                logger.exception("Error executing action %s: %s", act, ex)
                executed_results.append({"action": act, "error": str(ex)})

    response = {
        "org_id": org_id,
        "message": user_message,
        "agents_context": ctx,
        "llm_raw": raw_text,
        "structured": structured,
    }
    if executed_results:
        response["executed_actions"] = executed_results

    return response