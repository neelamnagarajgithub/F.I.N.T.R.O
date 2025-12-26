#!/usr/bin/env python3
"""
Collection & Intervention Agent

Purpose:
- Prioritize overdue receivables
- Draft personalized reminders
- Suggest interventions (discounts, payment plans, escalate)
- Score success probability and recommend channel
- Produce outputs and recovery/DSO metrics

Usage:
- Call `run_collections_agent(...)` with input lists/dicts described in the function docstring.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import math
import statistics
import asyncio
import os

# New imports: use Risk Agent (Agent 3) and Collision Agent (Agent 4)
from Risk_Anamoly_Agent.agent import run_risk_agent_async
from Liquidity_and_Collision_Detection_Agent.agent import CollisionAgent

# ----------------------------
# Data models
# ----------------------------

@dataclass
class OverdueItem:
    invoice_id: str
    customer_id: str
    amount: float
    due_date: str  # YYYY-MM-DD
    days_overdue: int
    status: str  # 'open', 'overdue', etc.

@dataclass
class CustomerProfile:
    customer_id: str
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    preferred_channel: Optional[str] = None  # 'sms', 'email', 'whatsapp', 'call'
    risk_score: float = 0.5  # 0..1 (higher = higher risk)
    payment_reliability_score: float = 0.5  # 0..1 (higher = more reliable)
    last_payment_date: Optional[str] = None

@dataclass
class CollisionInfo:
    date: str  # YYYY-MM-DD
    days_from_now: int
    severity: float  # arbitrary severity score (higher = more severe)

@dataclass
class QueueItem:
    invoice_id: str
    customer_id: str
    customer_name: str
    amount: float
    days_overdue: int
    collision_proximity: float
    priority_score: float
    recommended_intervention: str
    success_probability: float
    recommended_channel: str
    draft_message: str

@dataclass
class InterventionResult:
    prioritized_today: List[Dict[str, Any]]
    full_queue: List[Dict[str, Any]]
    drafted_reminders: Dict[str, str]  # invoice_id -> message
    success_probabilities: Dict[str, float]  # invoice_id -> %
    recommended_interventions: Dict[str, str]  # invoice_id -> intervention
    recovery_metrics: Dict[str, Any]
    channel_effectiveness: Dict[str, Any]
    dso_improvement_potential: Dict[str, Any]

# ----------------------------
# Helpers / heuristics
# ----------------------------

def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s.split("T")[0], "%Y-%m-%d")
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None

def _days_between(d: Optional[str]) -> int:
    parsed = _parse_date(d)
    if parsed is None:
        return 0
    return (datetime.now().date() - parsed.date()).days

def _collision_proximity_factor(collisions: List[CollisionInfo], target_date: Optional[str]) -> float:
    """
    Return a factor 0.1..2.0 (higher when collision is sooner and more severe)
    If an invoice date falls close to a collision date, increase proximity.
    We return 1.0 when no nearby collisions.
    """
    if not collisions or not target_date:
        return 1.0
    t = _parse_date(target_date)
    if not t:
        return 1.0
    min_factor = 1.0
    for c in collisions:
        cdate = _parse_date(c.date)
        if not cdate:
            continue
        days = (cdate.date() - t.date()).days
        # If collision occurs within next 14 days of invoice date, increase factor
        if -30 <= days <= 30:
            # proximity weight inversely proportional to abs(days)+1 and scaled by severity
            proximity = max(0.1, 1.0 + (1.0 / (abs(days) + 1)) * (c.severity or 1.0))
            # clamp
            proximity = min(proximity, 2.5)
            if proximity > min_factor:
                min_factor = proximity
    return min_factor

def _normalize(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))

def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))

# ----------------------------
# Core scoring & intervention logic
# ----------------------------

def compute_priority_score(
    risk_score: float,
    days_overdue: int,
    amount: float,
    collision_proximity: float,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Compute a priority score. Higher => handle earlier.
    Basic formula (heuristic):
      score = w1 * risk + w2 * normalized_days + w3 * normalized_amount + w4 * collision_proximity
    We then scale by product for sharper ranking.
    """
    if weights is None:
        weights = {"risk": 0.4, "days": 0.25, "amount": 0.25, "collision": 0.1}

    # normalize days and amount to reasonable ranges
    days_norm = _normalize(days_overdue, 0, 120)  # >120 days treat as saturated
    amount_norm = _normalize(math.log1p(amount), 0, math.log1p(10_000_000))  # log-scale normalizing to ~10M

    linear = (
        weights["risk"] * risk_score
        + weights["days"] * days_norm
        + weights["amount"] * amount_norm
        + weights["collision"] * _normalize(collision_proximity, 0, 2.5)
    )

    # combine linear and multiplicative effect to rank extremes higher
    score = linear * (1 + (risk_score * days_norm * amount_norm * (collision_proximity / 2.0)))
    return float(score)

def suggest_intervention(amount: float, days_overdue: int, risk_score: float, payment_reliability: float) -> str:
    """
    Suggest an intervention strategy based on simple rules:
      - small amounts & low days -> reminder (email/SMS)
      - medium amounts -> payment plan or discount
      - large amounts & high risk -> escalate / legal / dedicated collection
    """
    if amount < 50_000 and days_overdue < 30 and payment_reliability > 0.4:
        return "friendly_reminder"
    if amount < 200_000 and days_overdue < 60 and payment_reliability > 0.3:
        return "offer_payment_plan"
    if amount < 500_000 and risk_score < 0.6:
        return "early_discount_offer"
    if risk_score > 0.8 or days_overdue > 120:
        return "escalate_to_collections"
    # default
    return "phone_call_priority"

def compute_success_probability(
    risk_score: float,
    days_overdue: int,
    amount: float,
    payment_history_score: float,
    intervention: str
) -> float:
    """
    Heuristic probability model 0..1 using logistic function.
    Positive factors: payment_history_score (higher is better), intervention suitability
    Negative factors: risk_score, days_overdue, amount (scaled)
    """
    # base log-odds
    base = 0.0
    # negative contributions
    base -= 2.0 * risk_score
    base -= 0.01 * min(days_overdue, 365)  # each day reduces odds slightly
    base -= 0.000001 * amount  # scale down large amounts
    # positive contributions
    base += 2.5 * payment_history_score

    # intervention modifier
    if intervention == "friendly_reminder":
        base += 0.5
    elif intervention == "offer_payment_plan":
        base += 1.0
    elif intervention == "early_discount_offer":
        base += 0.8
    elif intervention == "phone_call_priority":
        base += 1.2
    elif intervention == "escalate_to_collections":
        base -= 0.2

    prob = _sigmoid(base)
    # clamp and return
    return float(max(0.0, min(1.0, prob)))

def recommend_channel(preferred: Optional[str], contact_email: Optional[str], contact_phone: Optional[str], intervention: str) -> str:
    """
    Recommend the best channel.
    Preference order:
      - if preferred channel provided use it
      - for high urgency interventions prefer 'call' or 'whatsapp'
      - otherwise choose email or sms based on availability
    """
    if preferred:
        return preferred
    if intervention in ("phone_call_priority", "escalate_to_collections"):
        if contact_phone:
            return "call"
        if contact_phone and "whatsapp" in contact_phone.lower():
            return "whatsapp"
    # low urgency
    if contact_email:
        return "email"
    if contact_phone:
        return "sms"
    return "email"

def draft_reminder(customer_name: str, invoice_id: str, amount: float, days_overdue: int, intervention: str) -> str:
    """
    Return a short template message customised by intervention
    """
    amount_display = f"₹{amount:,.2f}"
    if intervention == "friendly_reminder":
        return (f"Hi {customer_name},\n\n"
                f"This is a friendly reminder that invoice {invoice_id} of {amount_display}"
                f" is overdue by {days_overdue} days. Please let us know when we can expect payment.\n\nThanks.")
    if intervention == "offer_payment_plan":
        return (f"Hi {customer_name},\n\n"
                f"We can offer a flexible payment plan for invoice {invoice_id} ({amount_display}). "
                f"Please reply 'PLAN' and we'll send options.\n\nRegards.")
    if intervention == "early_discount_offer":
        return (f"Hi {customer_name},\n\n"
                f"If you can settle invoice {invoice_id} ({amount_display}) within 7 days, "
                f"we can offer a 2% early payment discount. Reply 'DISCOUNT' to accept.\n\nThanks.")
    if intervention == "phone_call_priority":
        return (f"Hi {customer_name},\n\n"
                f"Our accounts team will call regarding invoice {invoice_id} of {amount_display} overdue by {days_overdue} days. "
                f"Please be available to discuss payment options.\n\nRegards.")
    if intervention == "escalate_to_collections":
        return (f"Dear {customer_name},\n\n"
                f"Invoice {invoice_id} ({amount_display}) is significantly overdue. "
                f"We are escalating this matter to collections. Please contact us immediately to avoid further action.\n\nSincerely.")
    # fallback
    return (f"Hi {customer_name}, invoice {invoice_id} ({amount_display}) is overdue by {days_overdue} days. Please contact us.")

# ----------------------------
# Metrics helpers
# ----------------------------

def compute_recovery_metrics(prioritized: List[QueueItem], period_days: int = 30) -> Dict[str, Any]:
    """
    Estimate simple recovery metrics:
    - potential_recovery_today: sum of amounts * success_prob
    - target vs potential
    """
    potential = sum(q.amount * q.success_probability for q in prioritized)
    total = sum(q.amount for q in prioritized)
    avg_prob = statistics.mean([q.success_probability for q in prioritized]) if prioritized else 0.0
    return {
        "potential_recovery_amount": potential,
        "total_amount_contacted": total,
        "average_success_probability": avg_prob,
        "period_days": period_days
    }

def compute_channel_effectiveness(historical_channel_stats: Optional[Dict[str, Dict[str, float]]] = None) -> Dict[str, Any]:
    """
    Accepts historical metrics like:
      {'email': {'open_rate':0.4, 'response_rate':0.05, 'collection_pct':0.02}, ...}
    If none provided, return sensible defaults.
    """
    defaults = {
        "email": {"open_rate": 0.35, "response_rate": 0.06, "collection_pct": 0.03},
        "sms": {"open_rate": 0.85, "response_rate": 0.12, "collection_pct": 0.08},
        "whatsapp": {"open_rate": 0.9, "response_rate": 0.2, "collection_pct": 0.12},
        "call": {"open_rate": 1.0, "response_rate": 0.5, "collection_pct": 0.25}
    }
    if not historical_channel_stats:
        return defaults
    # merge with defaults
    out = {}
    for k, v in defaults.items():
        hist = historical_channel_stats.get(k, {}) if historical_channel_stats else {}
        merged = {**v, **hist}
        out[k] = merged
    return out

def estimate_dso_improvement(current_dso: float, potential_recovery: float, total_receivables: float) -> Dict[str, Any]:
    """
    Simple estimate: if we recover potential_recovery this period, how much DSO could drop.
    """
    if total_receivables <= 0:
        return {"current_dso": current_dso, "estimated_dso": current_dso, "delta_days": 0}
    # very rough: proportionate improvement
    recover_fraction = min(1.0, potential_recovery / total_receivables)
    estimated_dso = current_dso * (1 - 0.5 * recover_fraction)  # assume up to 50% reduction proportionally
    delta = current_dso - estimated_dso
    return {"current_dso": current_dso, "estimated_dso": round(estimated_dso, 2), "delta_days": round(delta, 2)}

# ----------------------------
# Main entry point
# ----------------------------

def run_collections_agent(
    org_id: int,
    overdue_items: List[Dict[str, Any]],
    customers: List[Dict[str, Any]],
    collisions: Optional[List[Dict[str, Any]]] = None,
    payment_history: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    historical_channel_stats: Optional[Dict[str, Dict[str, float]]] = None,
    top_k_calls_today: int = 10,
    current_dso: float = 60.0
) -> Dict[str, Any]:
    """
    Inputs:
      - org_id: org identifier (for logging only)
      - overdue_items: list of invoices (dict with keys: invoice_id, customer_id, amount, due_date, status)
      - customers: list of customer profiles (dict). Fields: customer_id, name, contact_email, contact_phone, preferred_channel,
                   risk_score (0..1), payment_reliability_score (0..1), last_payment_date
      - collisions: list of {'date':'YYYY-MM-DD', 'severity':float} (optional)
      - payment_history: mapping customer_id -> list of {payment_date, amount} (optional)
      - historical_channel_stats: optional channel metrics
      - top_k_calls_today: how many top items to recommend calling today
      - current_dso: current days sales outstanding (for DSO improvement estimate)

    Returns:
      Dict containing all required outputs (see agent PURPOSE)
    """

    # prepare data lookups
    cust_map: Dict[str, CustomerProfile] = {}
    for c in customers:
        cust_map[c.get("customer_id")] = CustomerProfile(
            customer_id=str(c.get("customer_id")),
            name=c.get("name") or c.get("customer_name") or f"Customer {c.get('customer_id')}",
            contact_email=c.get("contact_email"),
            contact_phone=c.get("contact_phone"),
            preferred_channel=c.get("preferred_channel"),
            risk_score=float(c.get("risk_score") or c.get("risk") or 0.5),
            payment_reliability_score=float(c.get("payment_reliability_score") or c.get("payment_reliability") or 0.5),
            last_payment_date=c.get("last_payment_date")
        )

    collision_objs: List[CollisionInfo] = []
    if collisions:
        for c in collisions:
            days_from_now = _days_between(c.get("date")) * -1  # negative if in future; we keep raw days difference usage elsewhere
            # compute days_from_now more usefully
            try:
                d = _parse_date(c.get("date"))
                days_from_now = (d.date() - datetime.now().date()).days
            except Exception:
                days_from_now = 999
            collision_objs.append(CollisionInfo(date=c.get("date"), days_from_now=days_from_now, severity=float(c.get("severity") or 1.0)))

    # compute per-invoice queue items
    queue: List[QueueItem] = []
    for inv in overdue_items:
        invoice_id = str(inv.get("invoice_id") or inv.get("id"))
        cid = str(inv.get("customer_id"))
        amount = float(inv.get("amount") or inv.get("remaining_amount") or inv.get("outstanding") or 0.0)
        due_date = inv.get("due_date") or inv.get("dueDate") or inv.get("date")
        days_overdue = int(inv.get("days_overdue") or _days_between(due_date))
        cust = cust_map.get(cid) or CustomerProfile(customer_id=cid, name=f"Customer {cid}")
        # compute collision proximity based on collisions list (higher => more urgent)
        collision_prox = _collision_proximity_factor(collision_objs, due_date)
        # compute priority
        score = compute_priority_score(cust.risk_score, days_overdue, amount, collision_prox)
        # payment history score: simple aggregation
        p_hist_list = (payment_history or {}).get(cid, [])
        # create a simple payment history score: fraction of on-time payments in last 12 months
        p_score = 0.5
        if p_hist_list:
            on_time = 0
            total = 0
            for p in p_hist_list:
                total += 1
                # simplistic: if payment_date within due date+15 days considered on time
                # We don't have invoice due dates here, so approximate by recency
                if _days_between(p.get("payment_date")) <= 90:
                    on_time += 1
            p_score = on_time / total if total else 0.5

        intervention = suggest_intervention(amount, days_overdue, cust.risk_score, cust.payment_reliability_score)
        success_prob = compute_success_probability(cust.risk_score, days_overdue, amount, p_score, intervention)
        channel = recommend_channel(cust.preferred_channel, cust.contact_email, cust.contact_phone, intervention)
        draft = draft_reminder(cust.name, invoice_id, amount, days_overdue, intervention)

        qi = QueueItem(
            invoice_id=invoice_id,
            customer_id=cid,
            customer_name=cust.name,
            amount=amount,
            days_overdue=days_overdue,
            collision_proximity=collision_prox,
            priority_score=score,
            recommended_intervention=intervention,
            success_probability=round(success_prob, 3),
            recommended_channel=channel,
            draft_message=draft
        )
        queue.append(qi)

    # sort descending by priority_score
    queue.sort(key=lambda x: x.priority_score, reverse=True)

    # prepare outputs
    prioritized_today = queue[:top_k_calls_today]
    drafted_reminders = {q.invoice_id: q.draft_message for q in queue}
    success_probabilities = {q.invoice_id: float(q.success_probability) for q in queue}
    recommended_interventions = {q.invoice_id: q.recommended_intervention for q in queue}

    # metrics
    recovery_metrics = compute_recovery_metrics(prioritized_today)
    channel_metrics = compute_channel_effectiveness(historical_channel_stats)
    total_receivables = sum(q.amount for q in queue)
    dso_est = estimate_dso_improvement(current_dso, recovery_metrics["potential_recovery_amount"], total_receivables)

    # prepare final serializable structures
    prioritized_today_out = [asdict(q) for q in prioritized_today]
    full_queue_out = [asdict(q) for q in queue]

    result = InterventionResult(
        prioritized_today=[dict(q) if isinstance(q, dict) else asdict(q) for q in prioritized_today],
        full_queue=full_queue_out,
        drafted_reminders=drafted_reminders,
        success_probabilities=success_probabilities,
        recommended_interventions=recommended_interventions,
        recovery_metrics=recovery_metrics,
        channel_effectiveness=channel_metrics,
        dso_improvement_potential=dso_est
    )

    # Convert to dict
    return asdict(result)

# ----------------------------
# Orchestrator: use Agent 3 (Risk) + Agent 4 (Collision) to run collections
# ----------------------------
async def run_collections_workflow(
    org_id: int,
    backend_url: Optional[str] = None,
    top_k_calls_today: int = 10,
    use_cached_collision: bool = True
) -> Dict[str, Any]:
    """
    Fetch required inputs from Agent 3 (risk) and Agent 4 (liquidity/collision),
    then run the local collections logic (run_collections_agent).

    Returns the same structure as run_collections_agent but orchestrated.
    """
    # 1) fetch risk outputs (overdue, customer risk scores, payment history)
    try:
        risk_output = await run_risk_agent_async(org_id)
    except Exception as e:
        risk_output = {}
    
    # flexible extraction from risk agent output
    overdue = risk_output.get("overdue_receivables") or risk_output.get("overdue") or risk_output.get("overdue_invoices") or []
    # Normalize overdue item fields expected by run_collections_agent
    normalized_overdue = []
    for inv in overdue:
        normalized_overdue.append({
            "invoice_id": str(inv.get("invoice_id") or inv.get("id") or inv.get("invoiceId") or ""),
            "customer_id": inv.get("customer_id") or inv.get("customerId") or inv.get("customer"),
            "amount": float(inv.get("remaining_amount") or inv.get("outstanding") or inv.get("amount") or 0.0),
            "due_date": inv.get("due_date") or inv.get("dueDate") or inv.get("date"),
            "days_overdue": int(inv.get("days_overdue") or 0),
            "status": inv.get("status") or inv.get("payment_status") or "open"
        })

    # customers: risk scores list -> customers list expected by run_collections_agent
    cust_scores = risk_output.get("customer_risk_scores") or risk_output.get("customer_scores") or []
    customers = []
    if isinstance(cust_scores, dict):
        # maybe mapping customer_id -> score
        for cid, score in cust_scores.items():
            customers.append({
                "customer_id": cid,
                "name": f"Customer {cid}",
                "risk_score": float(score),
                "payment_reliability_score": 0.5
            })
    else:
        for c in (cust_scores or []):
            customers.append({
                "customer_id": c.get("customer_id") or c.get("id") or c.get("customer"),
                "name": c.get("customer_name") or c.get("name") or f"Customer {c.get('customer_id') or c.get('id')}",
                "risk_score": float(c.get("risk_score") or c.get("risk") or 0.5),
                "payment_reliability_score": float(c.get("payment_reliability_score") or c.get("payment_reliability") or 0.5)
            })

    # payment history
    payment_history = risk_output.get("payment_history") or risk_output.get("payment_history_map") or {}

    # 2) fetch collisions from Agent 4
    collisions_list = []
    try:
        base = backend_url or os.getenv("API_BASE_URL", "https://fintro-backend-883163069340.asia-south1.run.app")
        coll_agent = CollisionAgent(base)
        coll_graph = await coll_agent.create_graph()
        coll_state = {"org_id": org_id, "current_step": "initialized"}
        coll_result = await coll_graph.ainvoke(coll_state)
        # coll_result may be a state dict or contain 'output'
        out = coll_result.get("output") if isinstance(coll_result, dict) and coll_result.get("output") else coll_result
        # Try a few keys
        collisions_list = (out.get("collision_analysis", {}).get("collisions_91d")
                           or out.get("collisions") or out.get("collision_list") or [])
        # normalize to minimal collision dicts
        normalized_collisions = []
        for c in collisions_list:
            normalized_collisions.append({
                "date": c.get("collision_date") or c.get("date") or c.get("forecast_date"),
                "severity": c.get("severity") or c.get("severity_score") or 1.0
            })
        collisions_list = normalized_collisions
    except Exception:
        collisions_list = []

    # 3) Call local collections engine
    result = run_collections_agent(
        org_id=org_id,
        overdue_items=normalized_overdue,
        customers=customers,
        collisions=collisions_list,
        payment_history=payment_history,
        historical_channel_stats=None,
        top_k_calls_today=top_k_calls_today,
        current_dso=60.0
    )

    # attach provenance
    result["_provenance"] = {
        "risk_agent_present": bool(risk_output),
        "collision_agent_present": bool(collisions_list)
    }

    return result

def run_collections_workflow_sync(org_id: int, backend_url: Optional[str] = None, top_k_calls_today: int = 10) -> Dict[str, Any]:
    """Sync wrapper for environments that can't await."""
    return asyncio.run(run_collections_workflow(org_id, backend_url=backend_url, top_k_calls_today=top_k_calls_today))

