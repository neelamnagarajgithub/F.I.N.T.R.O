import requests
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

# Small helpers for robust parsing
def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v in (None, "", False):
            return float(default)
        return float(v)
    except Exception:
        try:
            return float(str(v).replace(",", "").strip())
        except Exception:
            return float(default)

def _parse_date(s: Any, fallback_tzinfo=None) -> Optional[datetime]:
    if not s:
        return None
    try:
        # Normalize common ISO suffix
        ds = str(s).replace("Z", "+00:00")
        dt = datetime.fromisoformat(ds)
        if dt.tzinfo is None and fallback_tzinfo is not None:
            dt = dt.replace(tzinfo=fallback_tzinfo)
        return dt
    except Exception:
        return None
    
def format_currency_short(amount: float, currency: str = "$") -> str:
    """Return short human-readable currency (e.g. $185K, $1.2M)."""
    try:
        a = float(amount or 0.0)
    except Exception:
        a = 0.0
    sign = "-" if a < 0 else ""
    a_abs = abs(a)
    if a_abs >= 1_000_000:
        return f"{sign}{currency}{a_abs/1_000_000:.1f}M"
    if a_abs >= 1_000:
        return f"{sign}{currency}{a_abs/1_000:.1f}K"
    return f"{sign}{currency}{a_abs:,.0f}"
# ============================================================
# LOGGING SETUP
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# 1. STATE DEFINITIONS (TypedDict)
# ============================================================

class AnomalyDict(TypedDict, total=False):
    """Anomaly record"""
    type: str
    amount: float
    z_score: float
    severity: str
    date: str
    payment_id: str
    expected_range: str

class CustomerRiskScoreDict(TypedDict, total=False):
    """Customer risk score"""
    customer_id: int
    customer_name: str
    risk_score: float
    risk_level: str
    dso_days: float
    anomaly_count: int
    days_overdue_max: int

class VendorScoreDict(TypedDict, total=False):
    """Vendor reliability score"""
    vendor_id: int
    vendor_name: str
    reliability_score: float
    on_time_pct: float
    avg_payment_days: float
    recent_issues: int

class OverdueDict(TypedDict, total=False):
    """Overdue receivable"""
    invoice_id: str
    customer_id: int
    customer_name: str
    amount: float
    due_date: str
    days_overdue: int
    status: str

class DSODict(TypedDict, total=False):
    """DSO by customer"""
    customer_id: int
    customer_name: str
    avg_dso_days: float
    invoices_open: int
    total_outstanding_ar: float

class RiskState(TypedDict, total=False):
    """Complete Risk Agent State"""
    org_id: int
    payments: List[Dict[str, Any]]
    invoices: List[Dict[str, Any]]
    bills: List[Dict[str, Any]]
    customers: List[Dict[str, Any]]
    baseline_stats: Dict[str, float]
    anomalies: List[AnomalyDict]
    customer_risk_scores: List[CustomerRiskScoreDict]
    vendor_scores: List[VendorScoreDict]
    overdue_receivables: List[OverdueDict]
    dso_by_customer: List[DSODict]
    early_warnings: List[str]
    explanation: str
    timestamp: str
    status: str
    summary_stats: Dict[str, Any]
# ============================================================
# 2. FETCH MODULE
# ============================================================

BASE_URL = "https://fintro-backend-883163069340.asia-south1.run.app"  # HARDCODED

def fetch_data(org_id: int):
    """Fetch all required data from backend"""
    try:
        logger.info(f"[FETCH] Fetching payments for org {org_id}")
        payments_resp = requests.get(f"{BASE_URL}/payments/org/{org_id}", timeout=10)
        pr = payments_resp.json()
        if isinstance(pr, dict):
            payments = pr.get("payments") or pr.get("data") or []
        elif isinstance(pr, list):
            payments = pr
        else:
            payments = []
        logger.info(f"[FETCH] Got {len(payments)} payments")
        
        logger.info(f"[FETCH] Fetching invoices for org {org_id}")
        invoices_resp = requests.get(f"{BASE_URL}/invoices/org/{org_id}", timeout=10)
        ir = invoices_resp.json()
        if isinstance(ir, dict):
            invoices = ir.get("invoices") or ir.get("data") or []
        elif isinstance(ir, list):
            invoices = ir
        else:
            invoices = []
        logger.info(f"[FETCH] Got {len(invoices)} invoices")
        
        logger.info(f"[FETCH] Fetching bills for org {org_id}")
        bills_resp = requests.get(f"{BASE_URL}/bills/org/{org_id}", timeout=10)
        br = bills_resp.json()
        if isinstance(br, dict):
            bills = br.get("bills") or br.get("data") or []
        elif isinstance(br, list):
            bills = br
        else:
            bills = []
        logger.info(f"[FETCH] Got {len(bills)} bills")
        
        logger.info(f"[FETCH] Fetching customers for org {org_id}")
        customers_resp = requests.get(f"{BASE_URL}/customers/org/{org_id}", timeout=10)
        cr = customers_resp.json()
        if isinstance(cr, dict):
            customers = cr.get("customers") or cr.get("data") or []
        elif isinstance(cr, list):
            customers = cr
        else:
            customers = []
        logger.info(f"[FETCH] Got {len(customers)} customers")
        
        
        return payments, invoices, bills, customers
        
    except Exception as e:
        logger.error(f"[FETCH] Error: {e}")
        return [], [], [], []

# ============================================================
# 3. BASELINE MODULE
# ============================================================

def compute_baseline(payments: list) -> dict:
    """Establish baseline from 90-day historical payment data"""
    if not payments:
        logger.warning("[BASELINE] No payments data")
        return {"mean": 0, "std": 1, "max": 0, "min": 0, "count": 0, "median": 0}
    
    try:
        df = pd.DataFrame(payments)
        
        df["date"] = pd.to_datetime(
            df.get("payment_date", df.get("date")), 
            utc=True, 
            errors='coerce'
        )
        df["amount"] = pd.to_numeric(
            df.get("payment_amount", df.get("amount")), 
            errors='coerce'
        )
        
        df = df.dropna(subset=['date', 'amount'])
        
        if df.empty:
            logger.warning("[BASELINE] No valid data after filtering")
            return {"mean": 0, "std": 1, "max": 0, "min": 0, "count": 0, "median": 0}
        
        cutoff = pd.Timestamp.now(tz='UTC') - timedelta(days=90)
        df_90 = df[df["date"] >= cutoff]
        
        if df_90.empty:
            logger.warning("[BASELINE] No data in 90 days, using all")
            df_90 = df
        
        baseline = {
            "mean": float(df_90["amount"].mean()),
            "std": float(df_90["amount"].std()),
            "max": float(df_90["amount"].max()),
            "min": float(df_90["amount"].min()),
            "count": len(df_90),
            "median": float(df_90["amount"].median())
        }
        
        logger.info(f"[BASELINE] mean=₹{baseline['mean']:.2f}, std=₹{baseline['std']:.2f}")
        return baseline
        
    except Exception as e:
        logger.error(f"[BASELINE] Error: {e}")
        return {"mean": 0, "std": 1, "max": 0, "min": 0, "count": 0, "median": 0}

# ============================================================
# 4. ANOMALIES MODULE
# ============================================================

def detect_anomalies(payments: list, baseline: dict) -> list:
    """Detect anomalies using Z-score analysis (z-score > 2.5)"""
    anomalies = []
    mean = baseline.get("mean", 0)
    std = baseline.get("std", 1) or 1
    
    try:
        for payment in payments:
            try:
                amount = float(payment.get("payment_amount", payment.get("amount", 0)))
                z_score = (amount - mean) / std if std > 0 else 0
                
                if abs(z_score) > 2.5:
                    payment_type = payment.get("payment_type", "outflow")
                    
                    if payment_type == "outflow" and amount > mean:
                        anomaly_type = "spend_spike"
                    elif payment_type == "inflow" and amount < mean:
                        anomaly_type = "inflow_drop"
                    else:
                        anomaly_type = "unusual_pattern"
                    
                    severity = "high" if abs(z_score) > 4 else "medium"
                    
                    anomaly = {
                        "type": anomaly_type,
                        "amount": float(amount),
                        "z_score": round(float(z_score), 2),
                        "severity": severity,
                        "date": str(payment.get("payment_date", "")),
                        "payment_id": str(payment.get("payment_id", "")),
                        "expected_range": f"₹{mean - 2*std:.2f} to ₹{mean + 2*std:.2f}"
                    }
                    
                    anomalies.append(anomaly)
                    
            except (ValueError, TypeError):
                continue
        
        logger.info(f"[ANOMALIES] Detected {len(anomalies)}")
        return anomalies
        
    except Exception as e:
        logger.error(f"[ANOMALIES] Error: {e}")
        return []

# ============================================================
# 5. METRICS MODULE
# ============================================================

def calculate_dso(invoices: list, customers: list) -> list:
    """Calculate DSO (Days Sales Outstanding) by customer.
    More robust parsing for status, amounts, IDs, and dates.
    """
    result = []
    now = datetime.now(tz=datetime.now().astimezone().tzinfo)

    try:
        # Build a lenient customer map
        customer_map: Dict[Any, str] = {}
        for c in (customers or []):
            cid = c.get("customer_id") or c.get("id") or c.get("customerId") or c.get("customer")
            if cid is None:
                continue
            name = (
                c.get("customer_name")
                or c.get("customerName")
                or c.get("name")
                or f"Customer {cid}"
            )
            customer_map[str(cid)] = name

        customer_invoices: Dict[str, Dict[str, Any]] = {}

        for inv in invoices or []:
            status = (inv.get("payment_status") or inv.get("status") or "").lower()
            # Include common unpaid states
            if status not in ("open", "partial", "unpaid", "pending"):
                continue

            cid = inv.get("customer_id") or inv.get("customerId") or inv.get("customer")
            if cid is None:
                continue
            cid_key = str(cid)

            if cid_key not in customer_invoices:
                customer_invoices[cid_key] = {
                    "invoices": [],
                    "outstanding_ar": 0.0,
                }

            customer_invoices[cid_key]["invoices"].append(inv)
            remaining = _to_float(
                inv.get("remaining_amount")
                or inv.get("outstanding")
                or inv.get("amount_due")
                or inv.get("amount")
                or 0
            )
            customer_invoices[cid_key]["outstanding_ar"] += remaining

        for cid_key, data in customer_invoices.items():
            days_list: List[int] = []

            for inv in data["invoices"]:
                # Prefer invoice/issue date; fall back to created_at/date
                issue_dt = (
                    _parse_date(inv.get("issue_date"), now.tzinfo)
                    or _parse_date(inv.get("invoice_date"), now.tzinfo)
                    or _parse_date(inv.get("invoiceDate"), now.tzinfo)
                    or _parse_date(inv.get("created_date"), now.tzinfo)
                    or _parse_date(inv.get("created_at"), now.tzinfo)
                    or _parse_date(inv.get("date"), now.tzinfo)
                )
                if not issue_dt:
                    continue
                try:
                    days = (now - issue_dt).days
                    days_list.append(days)
                except Exception:
                    continue

            if days_list:
                avg_dso = sum(days_list) / len(days_list)
                result.append({
                    "customer_id": cid_key,
                    "customer_name": customer_map.get(cid_key, f"Customer {cid_key}"),
                    "avg_dso_days": round(avg_dso, 2),
                    "invoices_open": len(data["invoices"]),
                    "total_outstanding_ar": round(_to_float(data["outstanding_ar"]), 2),
                })

        logger.info(f"[METRICS] DSO for {len(result)} customers")
        return result

    except Exception as e:
        logger.error(f"[METRICS] Error: {e}")
        return []


def identify_overdue_receivables(invoices: list, customers: list) -> list:
    """Identify overdue receivables (past due date)"""
    overdue = []
    now = datetime.now(tz=datetime.now().astimezone().tzinfo)

    customer_map: Dict[Any, str] = {}
    for c in (customers or []):
        cid = c.get("customer_id") or c.get("id") or c.get("customerId") or c.get("customer")
        if cid is None:
            continue
        customer_map[str(cid)] = (
            c.get("customer_name")
            or c.get("customerName")
            or c.get("name")
            or f"Customer {cid}"
        )

    try:
        for inv in invoices or []:
            status = (inv.get("payment_status") or inv.get("status") or "").lower()
            if status not in ("open", "partial", "unpaid", "pending"):
                continue

            try:
                due_str = inv.get("due_date") or inv.get("dueDate")
                due = _parse_date(due_str, now.tzinfo)
                if not due:
                    continue

                if due < now:
                    days_overdue = (now - due).days
                    cid = inv.get("customer_id") or inv.get("customerId") or inv.get("customer")
                    cid_key = str(cid) if cid is not None else ""

                    overdue.append({
                        "invoice_id": str(inv.get("invoice_id") or inv.get("id") or ""),
                        "customer_id": cid,
                        "customer_name": customer_map.get(cid_key, "Unknown"),
                        "amount": _to_float(
                            inv.get("remaining_amount")
                            or inv.get("outstanding")
                            or inv.get("amount_due")
                            or inv.get("amount")
                            or 0
                        ),
                        "due_date": str(due_str),
                        "days_overdue": days_overdue,
                        "status": status,
                    })

            except Exception:
                continue

        overdue.sort(key=lambda x: x["days_overdue"], reverse=True)

        logger.info(f"[METRICS] Found {len(overdue)} overdue")
        return overdue

    except Exception as e:
        logger.error(f"[METRICS] Error: {e}")
        return []

# ============================================================
# 6. SCORING MODULE
# ============================================================

def calculate_customer_risk_score(dso_days: float, days_overdue_max: int, 
                                  anomaly_count: int, payment_reliability: float = 0.5) -> float:
    """Calculate customer risk score (0-100)"""
    try:
        score = 100
        
        # DSO impact (40%)
        if dso_days > 90:
            score -= 40
        elif dso_days > 60:
            score -= 30
        elif dso_days > 30:
            score -= 15
        
        # Overdue days impact (30%)
        if days_overdue_max > 60:
            score -= 30
        elif days_overdue_max > 30:
            score -= 20
        elif days_overdue_max > 0:
            score -= 10
        
        # Anomalies impact (20%)
        if anomaly_count > 3:
            score -= 20
        elif anomaly_count > 1:
            score -= 10
        
        # Payment reliability impact (10%)
        score -= (1 - payment_reliability) * 10
        
        return max(0, min(100, score))
        
    except Exception as e:
        logger.error(f"[SCORING] Error: {e}")
        return 50


def get_risk_level(risk_score: float) -> str:
    """Convert risk score to risk level"""
    if risk_score >= 80:
        return "low"
    elif risk_score >= 60:
        return "medium"
    elif risk_score >= 40:
        return "high"
    else:
        return "critical"

# ============================================================
# 7. VENDOR ANALYSIS MODULE (SKIPPED - NO VENDORS ENDPOINT)
# ============================================================

def analyze_vendor_reliability(bills: list) -> list:
    """Analyze vendor payment reliability from bills"""
    vendor_scores = []
    
    try:
        vendor_bills = {}
        for bill in bills:
            vid = bill.get("vendor_id")
            if not vid:
                continue
            
            if vid not in vendor_bills:
                vendor_bills[vid] = []
            vendor_bills[vid].append(bill)
        
        now = datetime.now(tz=datetime.now().astimezone().tzinfo)
        
        for vid, bills_list in vendor_bills.items():
            on_time_count = 0
            total_paid = 0
            payment_days_list = []
            
            for bill in bills_list:
                status = bill.get("payment_status", bill.get("status", ""))
                if status == "paid":
                    total_paid += 1
                    
                    try:
                        due_str = bill.get("due_date")
                        paid_str = bill.get("payment_date")
                        
                        if due_str and paid_str:
                            due = datetime.fromisoformat(str(due_str).replace('Z', '+00:00'))
                            paid = datetime.fromisoformat(str(paid_str).replace('Z', '+00:00'))
                            
                            if due.tzinfo is None:
                                due = due.replace(tzinfo=now.tzinfo)
                            if paid.tzinfo is None:
                                paid = paid.replace(tzinfo=now.tzinfo)
                            
                            if paid <= due:
                                on_time_count += 1
                            
                            payment_days = (paid - due).days
                            payment_days_list.append(payment_days)
                    except Exception:
                        continue
            
            if total_paid > 0:
                on_time_pct = (on_time_count / total_paid) * 100
                avg_payment_days = sum(payment_days_list) / len(payment_days_list) if payment_days_list else 0
                
                reliability_score = on_time_pct * 0.8 + max(0, 100 - abs(avg_payment_days) * 10) * 0.2
                
                vendor_scores.append({
                    "vendor_id": vid,
                    "vendor_name": f"Vendor {vid}",
                    "reliability_score": round(reliability_score, 2),
                    "on_time_pct": round(on_time_pct, 2),
                    "avg_payment_days": round(avg_payment_days, 2),
                    "recent_issues": total_paid - on_time_count
                })
        
        logger.info(f"[VENDORS] Analyzed {len(vendor_scores)} vendors from bills")
        return vendor_scores
        
    except Exception as e:
        logger.error(f"[VENDORS] Error: {e}")
        return []

# ============================================================
# 8. EARLY WARNINGS MODULE
# ============================================================

def generate_early_warnings(state: dict) -> list:
    """Generate early warning indicators based on risk analysis"""
    warnings = []
    
    try:
        anomaly_count = len(state.get("anomalies", []))
        if anomaly_count > 5:
            warnings.append(f"🚨 CRITICAL: {anomaly_count} spending anomalies detected")
        elif anomaly_count > 2:
            warnings.append(f"⚠️  WARNING: {anomaly_count} unusual spending patterns")
        
        overdue_count = len(state.get("overdue_receivables", []))
        if overdue_count > 10:
            warnings.append(f"🚨 CRITICAL: {overdue_count} invoices overdue")
        elif overdue_count > 5:
            warnings.append(f"⚠️  WARNING: {overdue_count} invoices past due date")
        
        high_risk_customers = [
            c for c in state.get("customer_risk_scores", []) 
            if c.get("risk_level") in ("high", "critical")
        ]
        if len(high_risk_customers) > 3:
            warnings.append(f"🚨 CRITICAL: {len(high_risk_customers)} customers at risk")
        elif high_risk_customers:
            names = ", ".join([c.get("customer_name") for c in high_risk_customers[:3]])
            warnings.append(f"⚠️  WARNING: Customers at risk: {names}")
        
        dso_list = [d.get("avg_dso_days", 0) for d in state.get("dso_by_customer", [])]
        if dso_list:
            avg_dso = sum(dso_list) / len(dso_list)
            if avg_dso > 60:
                warnings.append(f"⚠️  WARNING: Average DSO is {avg_dso:.0f} days (above 60-day target)")
        
        unreliable_vendors = [
            v for v in state.get("vendor_scores", [])
            if v.get("reliability_score", 100) < 60
        ]
        if unreliable_vendors:
            warnings.append(f"⚠️  WARNING: {len(unreliable_vendors)} vendors with reliability concerns")
        
        logger.info(f"[WARNINGS] Generated {len(warnings)} warnings")
        return warnings
        
    except Exception as e:
        logger.error(f"[WARNINGS] Error: {e}")
        return []

# ============================================================
# 9. LANGGRAPH NODES
# ============================================================

def fetch_node(state: RiskState) -> RiskState:
    """Node 1: Fetch data"""
    logger.info(f"[FETCH_NODE] Org {state['org_id']}")
    
    try:
        payments, invoices, bills, customers = fetch_data(state['org_id'])
        state.update({
            'payments': payments,
            'invoices': invoices,
            'bills': bills,
            'customers': customers
        })
    except Exception as e:
        logger.error(f"[FETCH_NODE] Error: {e}")
        state.update({'payments': [], 'invoices': [], 'bills': [], 'customers': []})
    
    return state


def baseline_node(state: RiskState) -> RiskState:
    """Node 2: Establish baseline"""
    logger.info("[BASELINE_NODE]")
    baseline = compute_baseline(state['payments'])
    state['baseline_stats'] = baseline
    return state


def anomalies_node(state: RiskState) -> RiskState:
    """Node 3: Detect anomalies"""
    logger.info("[ANOMALIES_NODE]")
    anomalies = detect_anomalies(state['payments'], state['baseline_stats'])
    state['anomalies'] = anomalies
    return state


def metrics_node(state: RiskState) -> RiskState:
    """Node 4: Calculate metrics"""
    logger.info("[METRICS_NODE]")
    state['dso_by_customer'] = calculate_dso(state['invoices'], state['customers'])
    state['overdue_receivables'] = identify_overdue_receivables(state['invoices'], state['customers'])
    return state


def scoring_node(state: RiskState) -> RiskState:
    """Node 5: Score customers"""
    logger.info("[SCORING_NODE]")
    
    risk_scores = []
    
    dso_map = {str(d.get('customer_id')): d for d in (state.get('dso_by_customer') or [])}
    overdue_map = {}
    for o in state['overdue_receivables']:
        cid = o['customer_id']
        if cid not in overdue_map:
            overdue_map[cid] = []
        overdue_map[cid].append(o['days_overdue'])
    
    for customer in (state.get('customers') or []):
        cid_raw = customer.get('customer_id') or customer.get('id') or customer.get('customerId') or customer.get('customer')
        cid_key = str(cid_raw) if cid_raw is not None else ""
        dso_days = dso_map.get(cid_key, {}).get('avg_dso_days', 0)
        max_overdue = max(overdue_map.get(cid_raw, [0])) if cid_raw in overdue_map else 0
        reliability = customer.get('payment_reliability_score', customer.get('reliability', 0.5))
        
        risk_score = calculate_customer_risk_score(
            dso_days=dso_days,
            days_overdue_max=max_overdue,
            anomaly_count=0,
            payment_reliability=reliability
        )
        
        risk_scores.append({
            "customer_id": cid_raw,
            "customer_name": customer.get('customer_name') or customer.get('customerName') or customer.get('name') or f"Customer {cid_key}",
            "risk_score": round(risk_score, 2),
            "risk_level": get_risk_level(risk_score),
            "dso_days": dso_days,
            "anomaly_count": 0,
            "days_overdue_max": max_overdue
        })
    
    state['customer_risk_scores'] = risk_scores
    return state


def vendors_node(state: RiskState) -> RiskState:
    """Node 6: Analyze vendors from bills"""
    logger.info("[VENDORS_NODE]")
    vendor_scores = analyze_vendor_reliability(state['bills'])
    state['vendor_scores'] = vendor_scores
    return state


def warnings_node(state: RiskState) -> RiskState:
    """Node 7: Generate warnings"""
    logger.info("[WARNINGS_NODE]")
    state['early_warnings'] = generate_early_warnings(state)
    return state


def finalize_node(state: RiskState) -> RiskState:
    """Node 8: Finalize"""
    logger.info("[FINALIZE_NODE]")
    state['timestamp'] = datetime.now().isoformat()
    state['status'] = 'success'

    # --- Summary / dashboard stats ---
    try:
        customer_scores = state.get('customer_risk_scores', []) or []
        dso_list = state.get('dso_by_customer', []) or []
        overdue = state.get('overdue_receivables', []) or []

        # High-risk customers (high or critical)
        high_risk_customers = [c for c in customer_scores if c.get('risk_level') in ('high', 'critical')]
        high_risk_count = len(high_risk_customers)

        # Map DSO entries by customer_id (coerce to str)
        dso_map = {str(d.get('customer_id')): d for d in dso_list}

        # Exposure: try sum of total_outstanding_ar for high-risk customers from DSO map
        exposure_sum = 0.0
        for hr in high_risk_customers:
            cid = hr.get('customer_id')
            if cid is None:
                continue
            d = dso_map.get(str(cid))
            if d:
                exposure_sum += _to_float(d.get('total_outstanding_ar', 0.0))

        # If exposure still zero, fall back to summing overdue receivables for those customers
        if exposure_sum == 0 and high_risk_customers:
            hr_ids = {str(c.get('customer_id')) for c in high_risk_customers}
            for o in overdue:
                if str(o.get('customer_id')) in hr_ids:
                    exposure_sum += _to_float(o.get('amount', 0.0))

        # AVG DSO across customers with DSO data
        avg_dso = 0.0
        if dso_list:
            avg_dso = sum(_to_float(d.get('avg_dso_days', 0.0)) for d in dso_list) / max(1, len(dso_list))

        # Total overdue receivables (sum of amounts from overdue list)
        total_overdue = sum(_to_float(o.get('amount', 0.0)) for o in overdue)

        state['summary_stats'] = {
            "high_risk_customers_count": int(high_risk_count),
            "high_risk_exposure": round(exposure_sum, 2),
            "high_risk_exposure_display": format_currency_short(exposure_sum, "$"),
            "avg_dso_days": round(avg_dso, 2),
            "avg_dso_display": str(int(round(avg_dso))) if avg_dso else "0",
            "total_overdue_receivables": round(total_overdue, 2),
            "total_overdue_display": format_currency_short(total_overdue, "$")
        }
    except Exception as e:
        logger.error(f"[FINALIZE_NODE] Error computing summary_stats: {e}")
        state['summary_stats'] = {
            "high_risk_customers_count": 0,
            "high_risk_exposure": 0.0,
            "high_risk_exposure_display": format_currency_short(0.0, "$"),
            "avg_dso_days": 0.0,
            "avg_dso_display": "0",
            "total_overdue_receivables": 0.0,
            "total_overdue_display": format_currency_short(0.0, "$")
        }

    return state
# ============================================================
# 10. BUILD LANGGRAPH
# ============================================================

def build_graph():
    """Build LangGraph workflow"""
    graph = StateGraph(RiskState)
    
    graph.add_node("fetch", fetch_node)
    graph.add_node("baseline", baseline_node)
    graph.add_node("anomalies", anomalies_node)
    graph.add_node("metrics", metrics_node)
    graph.add_node("scoring", scoring_node)
    graph.add_node("vendors", vendors_node)
    graph.add_node("warnings", warnings_node)
    graph.add_node("finalize", finalize_node)
    
    graph.set_entry_point("fetch")
    graph.add_edge("fetch", "baseline")
    graph.add_edge("baseline", "anomalies")
    graph.add_edge("anomalies", "metrics")
    graph.add_edge("metrics", "scoring")
    graph.add_edge("scoring", "vendors")
    graph.add_edge("vendors", "warnings")
    graph.add_edge("warnings", "finalize")
    graph.add_edge("finalize", END)
    
    return graph.compile()


risk_agent = build_graph()


import asyncio
from typing import Dict, Any

def run_risk_agent(org_id: int) -> Dict[str, Any]:
    """Run the risk agent synchronously (callable from other sync code)."""
    return risk_agent.invoke({"org_id": org_id})

async def run_risk_agent_async(org_id: int) -> Dict[str, Any]:
    """Run the risk agent in a threadpool so callers can await without blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: risk_agent.invoke({"org_id": org_id}))

