#!/usr/bin/env python3
"""
Agent 2: Forecasting Agent
Predicts cash flow 13 weeks ahead using Random Forest ML model
"""

from langgraph.graph import StateGraph, START, END
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import logging
import json
import os
import requests
import asyncio

logger = logging.getLogger(__name__)

class ForecastingAgent:
    """
    Agent 2: Forecasting
    
    Predicts cash flow 13 weeks (91 days) ahead with:
    - Random Forest ML model
    - Confidence intervals (95%, 5%)
    - Top inflows/outflows identification
    - MAPE accuracy metrics
    """
    
    def __init__(self):
        self.agent_id = "agent_2_forecasting"
        self.model = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.feature_means = {}
        self.feature_stds = {}
    

    def _api_base(self) -> str:
        return os.getenv("API_BASE_URL", "https://fintro-backend-883163069340.asia-south1.run.app")

    def _safe_date_parse(self, s):
        if s is None:
            return None
        if isinstance(s, datetime):
            return s.date()
        try:
            return datetime.fromisoformat(str(s)).date()
        except Exception:
            try:
                return datetime.strptime(str(s), "%Y-%m-%d").date()
            except Exception:
                return None

    async def create_graph(self):
        """Create LangGraph workflow"""
        workflow = StateGraph(Dict[str, Any])
        
        workflow.add_node("load_historical", self.load_historical_data)
        workflow.add_node("analyze_seasonality", self.analyze_seasonality)
        workflow.add_node("prepare_features", self.prepare_features)
        workflow.add_node("train_model", self.train_model)
        workflow.add_node("generate_forecast", self.generate_forecast)
        workflow.add_node("identify_drivers", self.identify_drivers)
        workflow.add_node("prepare_output", self.prepare_output)
        
        workflow.add_edge(START, "load_historical")
        workflow.add_edge("load_historical", "analyze_seasonality")
        workflow.add_edge("analyze_seasonality", "prepare_features")
        workflow.add_edge("prepare_features", "train_model")
        workflow.add_edge("train_model", "generate_forecast")
        workflow.add_edge("generate_forecast", "identify_drivers")
        workflow.add_edge("identify_drivers", "prepare_output")
        workflow.add_edge("prepare_output", END)
        
        return workflow.compile()
    
    # ============================================================
    # STEP 1: Load Historical Data
    # ============================================================
    async def load_historical_data(self, state: Dict) -> Dict:
        """Load 12+ months of historical transactions via payments HTTP API (with sensible defaults)."""
        logger.info(f"[{self.agent_id}] Step 1: Loading historical data (HTTP)")

        org_id = state.get("org_id")
        if not org_id:
            state["error"] = "missing org_id"
            state["current_step"] = "error"
            return state

        # Optional period bounds from state
        start = state.get("period_start")
        end = state.get("period_end")

        # Defaults and config
        base_url = os.getenv("API_BASE_URL", "https://fintro-backend-883163069340.asia-south1.run.app").rstrip("/")
        # default to last 365 days if start not provided
        if not start:
            start_date = (datetime.now().date() - timedelta(days=365))
        else:
            start_date = start if isinstance(start, (datetime,)) else start
            if isinstance(start_date, datetime):
                start_date = start_date.date()
        if end and isinstance(end, datetime):
            end_date = end.date()
        else:
            end_date = end

        params = {}
        if start_date:
            params["from"] = (
                start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date)
            )
        if end_date:
            params["to"] = end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date)

        url = f"{base_url}/payments/org/{org_id}"

        try:
            resp = requests.get(url, params=params or None, timeout=15)
            resp.raise_for_status()
            payments = resp.json().get("payments", []) or []
        except Exception as exc:
            logger.exception(f"[{self.agent_id}] Failed to fetch payments: {exc}")
            state["error"] = f"failed to fetch payments: {exc}"
            state["current_step"] = "error"
            return state

        if not payments:
            logger.warning(f"[{self.agent_id}] No payments returned for org {org_id}")
            state["error"] = "no_payments"
            state["current_step"] = "error"
            return state

        # Aggregate net change per date: inflow positive, outflow negative
        from collections import defaultdict
        date_map = defaultdict(float)

        for p in payments:
            pd_raw = p.get("payment_date") or p.get("date") or p.get("paymentDate")
            if pd_raw is None:
                continue

            # try several parsers
            parsed = None
            if isinstance(pd_raw, datetime):
                parsed = pd_raw.date()
            else:
                try:
                    parsed = datetime.fromisoformat(str(pd_raw)).date()
                except Exception:
                    try:
                        parsed = datetime.strptime(str(pd_raw), "%Y-%m-%d").date()
                    except Exception:
                        # skip unparsable
                        continue

            amt = p.get("payment_amount") or p.get("amount") or p.get("paymentAmount") or 0
            try:
                amt = float(amt)
            except Exception:
                try:
                    amt = float(str(amt).replace(",", ""))
                except Exception:
                    amt = 0.0

            ptype = (p.get("payment_type") or p.get("type") or "").lower()
            if ptype == "inflow":
                date_map[parsed] += amt
            elif ptype == "outflow":
                date_map[parsed] -= amt
            else:
                sign = p.get("sign")
                if sign in ("+", 1, "1", True):
                    date_map[parsed] += amt
                elif sign in ("-", -1, "-1", False):
                    date_map[parsed] -= amt
                else:
                    date_map[parsed] += amt

        sorted_dates = sorted(date_map.keys())
        record_count = len(sorted_dates)

        # configurable minimum and partial-data policy
        MIN_DAYS = int(os.getenv("MIN_HISTORICAL_DAYS", "90"))
        ALLOW_PARTIAL = os.getenv("ALLOW_PARTIAL_HISTORY", "false").lower() in ("1", "true", "yes", "y")

        if record_count < MIN_DAYS:
            logger.warning(f"[{self.agent_id}] Insufficient data: {record_count} days (required {MIN_DAYS})")
            if not ALLOW_PARTIAL:
                state["error"] = "Insufficient historical data"
                state["current_step"] = "error"
                return state
            # otherwise proceed but mark partial
            state["partial_history"] = True

        dates = sorted_dates
        net_changes = [float(date_map[d]) for d in dates]

        avg_daily_net = float(np.mean(net_changes)) if net_changes else 0.0
        std_daily_net = float(np.std(net_changes)) if net_changes else 0.0

        state["historical_data"] = {
            "dates": dates,
            "net_changes": net_changes,
            "record_count": record_count,
            "start_date": dates[0] if dates else None,
            "end_date": dates[-1] if dates else None,
            "avg_daily_net": avg_daily_net,
            "std_daily_net": std_daily_net,
        }

        state["current_step"] = "data_loaded"
        logger.info(f"[{self.agent_id}] Loaded {record_count} days of history (from payments API)")

        return state
    
    # ============================================================
    # STEP 2: Analyze Seasonality & Patterns
    # ============================================================
    async def analyze_seasonality(self, state: Dict) -> Dict:
        """Detect seasonality, trends, and patterns"""
        logger.info(f"[{self.agent_id}] Step 2: Analyzing seasonality")
        
        if state.get('error'):
            return state
        
        net_changes = np.array(state['historical_data']['net_changes'])
        dates = state['historical_data']['dates']
        
        # Aggregate by day of week
        dow_patterns = {}  # 0=Monday, 6=Sunday
        for date, change in zip(dates, net_changes):
            dow = date.weekday()
            if dow not in dow_patterns:
                dow_patterns[dow] = []
            dow_patterns[dow].append(change)
        
        # Calculate average by day of week
        dow_avg = {}
        for dow in range(7):
            if dow in dow_patterns:
                dow_avg[dow] = np.mean(dow_patterns[dow])
            else:
                dow_avg[dow] = 0
        
        # Aggregate by day of month (for payroll/rent patterns)
        dom_patterns = {}  # 1-31
        for date, change in zip(dates, net_changes):
            dom = date.day
            if dom not in dom_patterns:
                dom_patterns[dom] = []
            dom_patterns[dom].append(change)
        
        dom_avg = {}
        for dom in range(1, 32):
            if dom in dom_patterns:
                dom_avg[dom] = np.mean(dom_patterns[dom])
            else:
                dom_avg[dom] = None
        
        # Calculate trend (if increasing or decreasing)
        x = np.arange(len(net_changes))
        # Compute linear trend slope (guard when too few points)
        if len(net_changes) >= 2:
            z = np.polyfit(x, net_changes, 1)
            trend_slope = float(z[0])
        else:
            trend_slope = 0.0
        
        # Volatility (standard deviation)
        volatility = np.std(net_changes)
        mean_net = np.mean(net_changes)
        
        state['seasonality'] = {
            'day_of_week_avg': dow_avg,
            'day_of_month_avg': dom_avg,
            'trend_slope': float(trend_slope),
            'volatility': float(volatility),
            'mean_net_daily': float(mean_net),
            'seasonality_strength': 'strong' if volatility > abs(mean_net) * 0.5 else 'moderate'
        }
        
        state['current_step'] = 'seasonality_analyzed'
        
        logger.info(f"[{self.agent_id}] Seasonality detected: {state['seasonality']['seasonality_strength']}")
        
        return state
    
    # ============================================================
    # STEP 3: Prepare ML Features
    # ============================================================
    async def prepare_features(self, state: Dict) -> Dict:
        """Prepare features for Random Forest model"""
        logger.info(f"[{self.agent_id}] Step 3: Preparing features")
        
        if state.get('error'):
            return state
        
        dates = state['historical_data']['dates']
        net_changes = state['historical_data']['net_changes']
        seasonality = state['seasonality']
        
        X = []  # Features
        y = []  # Target (net change)
        
        for i, (date, change) in enumerate(zip(dates, net_changes)):
            # Feature engineering
            dow = date.weekday()  # 0-6
            dom = date.day  # 1-31
            month = date.month  # 1-12
            is_start_month = 1 if dom <= 5 else 0
            is_end_month = 1 if dom >= 25 else 0
            
            # Lagged features (previous days)
            lag_1 = net_changes[i-1] if i >= 1 else 0
            lag_7 = net_changes[i-7] if i >= 7 else 0
            lag_30 = net_changes[i-30] if i >= 30 else 0
            
            # Rolling averages
            rolling_7 = np.mean(net_changes[max(0, i-7):i]) if i > 0 else 0
            rolling_30 = np.mean(net_changes[max(0, i-30):i]) if i > 0 else 0
            
            # Feature vector: [dow, dom, month, is_start, is_end, lag1, lag7, lag30, rolling7, rolling30]
            features = [
                dow,
                dom,
                month,
                is_start_month,
                is_end_month,
                lag_1,
                lag_7,
                lag_30,
                rolling_7,
                rolling_30
            ]
            
            X.append(features)
            y.append(change)
        
        X = np.array(X)
        y = np.array(y)
        
        # Split into train (first 80%) and validation (last 20%)
        split_idx = int(len(X) * 0.8)
        X_train = X[:split_idx]
        y_train = y[:split_idx]
        X_val = X[split_idx:]
        y_val = y[split_idx:]
        
        state['X_train'] = X_train
        state['y_train'] = y_train
        state['X_val'] = X_val
        state['y_val'] = y_val
        state['feature_names'] = [
            'day_of_week', 'day_of_month', 'month',
            'is_start_month', 'is_end_month',
            'lag_1', 'lag_7', 'lag_30',
            'rolling_7', 'rolling_30'
        ]
        
        state['current_step'] = 'features_prepared'
        
        logger.info(f"[{self.agent_id}] Features prepared: {X.shape} records, {X.shape} features")
        
        return state
    
    # ============================================================
    # STEP 4: Train Random Forest Model
    # ============================================================
    async def train_model(self, state: Dict) -> Dict:
        """Train Random Forest model"""
        logger.info(f"[{self.agent_id}] Step 4: Training model")
        
        if state.get('error'):
            return state
        
        X_train = state['X_train']
        y_train = state['y_train']
        X_val = state['X_val']
        y_val = state['y_val']
        
        # Train model
        self.model.fit(X_train, y_train)
        
        # Evaluate on validation set
        y_pred_val = self.model.predict(X_val)
        
        # Calculate MAPE (Mean Absolute Percentage Error)
        mape = np.mean(np.abs((y_val - y_pred_val) / (np.abs(y_val) + 1))) * 100
        
        # Calculate RMSE
        rmse = np.sqrt(np.mean((y_val - y_pred_val) ** 2))
        
        # Feature importance
        feature_importance = dict(zip(
            state['feature_names'],
            self.model.feature_importances_
        ))
        
        state['model_info'] = {
            'model_type': 'RandomForestRegressor',
            'model_version': '1.0',
            'n_estimators': 200,
            'max_depth': 15,
            'training_samples': len(X_train),
            'validation_samples': len(X_val),
            'mape': float(mape),
            'rmse': float(rmse),
            'training_date': datetime.now().isoformat(),
            'feature_importance': feature_importance
        }
        
        state['current_step'] = 'model_trained'
        
        logger.info(f"[{self.agent_id}] Model trained: MAPE={mape:.2f}%, RMSE={rmse:.0f}")
        
        return state
    
    # ============================================================
    # STEP 5: Generate 91-Day Forecast
    # ============================================================
    async def generate_forecast(self, state: Dict) -> Dict:
        """Generate 91-day forecast with confidence intervals (uses payments API for balances)"""
        logger.info(f"[{self.agent_id}] Step 5: Generating forecast")

        if state.get('error'):
            return state

        net_changes = state['historical_data']['net_changes']
        dates = state['historical_data']['dates']
        last_date = dates[-1]

        forecast_results = []
        # start from opening_balance if provided, otherwise 0
        current_balance = float(state.get('opening_balance') or 0)
        predicted_daily_changes = []

        org_id = state.get('org_id')

        # Try to compute current balance by summing payments up to last_date
        try:
            base = self._api_base().rstrip("/")
            resp = requests.get(f"{base}/payments/org/{org_id}", timeout=10)
            resp.raise_for_status()
            payments_all = resp.json().get("payments", [])
        except Exception:
            payments_all = []

        for p in payments_all:
            pd_raw = p.get("payment_date") or p.get("date") or p.get("paymentDate")
            parsed = self._safe_date_parse(pd_raw)
            if parsed is None:
                continue
            if parsed <= last_date:
                amt = p.get("payment_amount") or p.get("amount") or p.get("paymentAmount") or 0
                try:
                    amt = float(amt)
                except Exception:
                    try:
                        amt = float(str(amt).replace(",", ""))
                    except Exception:
                        amt = 0.0
                ptype = (p.get("payment_type") or p.get("type") or "").lower()
                if ptype == "inflow":
                    current_balance += amt
                elif ptype == "outflow":
                    current_balance -= amt
                else:
                    # default treat as signed amount
                    current_balance += amt

        # Generate 91-day forecast
        for day_offset in range(91):
            forecast_date = last_date + timedelta(days=day_offset + 1)

            # Create feature vector
            dow = forecast_date.weekday()
            dom = forecast_date.day
            month = forecast_date.month
            is_start = 1 if dom <= 5 else 0
            is_end = 1 if dom >= 25 else 0

            # Use recent lagged values
            lag_1 = predicted_daily_changes[-1] if predicted_daily_changes else np.mean(net_changes)
            lag_7 = predicted_daily_changes[-7] if len(predicted_daily_changes) >= 7 else np.mean(net_changes)
            lag_30 = predicted_daily_changes[-30] if len(predicted_daily_changes) >= 30 else np.mean(net_changes)

            rolling_7 = np.mean(predicted_daily_changes[-7:]) if predicted_daily_changes else np.mean(net_changes)
            rolling_30 = np.mean(predicted_daily_changes[-30:]) if predicted_daily_changes else np.mean(net_changes)

            X_forecast = np.array([[
                dow, dom, month, is_start, is_end,
                lag_1, lag_7, lag_30, rolling_7, rolling_30
            ]])

            # Predict
            predicted_change = float(self.model.predict(X_forecast))
            predicted_daily_changes.append(predicted_change)

            # Add to running balance
            current_balance += predicted_change

            # Calculate confidence intervals using residuals (guard against empty validation)
            if state.get('X_val') is not None and len(state.get('X_val', [])) > 0:
                residuals = state['y_val'] - self.model.predict(state['X_val'])
                residual_std = np.std(residuals)
            else:
                residual_std = float(np.std(net_changes)) if len(net_changes) > 0 else 0.0

            confidence_95 = current_balance + (1.96 * residual_std)
            confidence_5 = current_balance - (1.96 * residual_std)

            forecast_results.append({
                'date': forecast_date.strftime('%Y-%m-%d'),
                'predicted_balance': round(float(current_balance), 2),
                'daily_change': round(predicted_change, 2),
                'confidence_95': round(float(confidence_95), 2),
                'confidence_5': round(float(confidence_5), 2),
                'confidence_level': 0.95
            })

        state['forecast_results'] = forecast_results
        state['predicted_daily_changes'] = predicted_daily_changes
        state['current_step'] = 'forecast_generated'

        logger.info(f"[{self.agent_id}] Generated 91-day forecast")

        return state
    
    # ============================================================
    # STEP 6: Identify Top Drivers (Inflows & Outflows)
    # ============================================================
    async def identify_drivers(self, state: Dict) -> Dict:
        """Identify top inflows and outflows (uses customers/invoices/bills APIs)"""
        logger.info(f"[{self.agent_id}] Step 6: Identifying drivers")

        if state.get('error'):
            return state

        org_id = state.get('org_id')
        base = self._api_base().rstrip("/")

        # Fetch customers
        try:
            resp = requests.get(f"{base}/customers/org/{org_id}", timeout=10)
            resp.raise_for_status()
            customers = resp.json().get("customers", []) or resp.json()
        except Exception:
            customers = []

        # Fetch invoices
        try:
            resp = requests.get(f"{base}/invoices/org/{org_id}", timeout=10)
            resp.raise_for_status()
            invoices = resp.json().get("invoices", []) or resp.json()
        except Exception:
            invoices = []

        # Fetch bills
        try:
            resp = requests.get(f"{base}/bills/org/{org_id}", timeout=10)
            resp.raise_for_status()
            bills = resp.json().get("bills", []) or resp.json()
        except Exception:
            bills = []

        # Aggregate invoices by customer for outstanding AR and open invoices
        per_customer = {}
        for inv in invoices:
            cid = inv.get("customer_id") or inv.get("customerId") or inv.get("customer")
            status = (inv.get("payment_status") or inv.get("status") or "").lower()
            remaining = inv.get("remaining_amount") or inv.get("outstanding") or inv.get("amount_due") or 0
            try:
                remaining = float(remaining)
            except Exception:
                try:
                    remaining = float(str(remaining).replace(",", ""))
                except Exception:
                    remaining = 0.0

            # compute collection days if possible
            invoice_date = self._safe_date_parse(inv.get("invoice_date") or inv.get("date") or inv.get("invoiceDate"))
            due_date = self._safe_date_parse(inv.get("due_date") or inv.get("dueDate"))

            if cid not in per_customer:
                per_customer[cid] = {
                    "outstanding_ar": 0.0,
                    "open_count": 0,
                    "collection_days_total": 0.0,
                    "collection_count": 0
                }

            if status in ("open", "partial", "unpaid"):
                per_customer[cid]["outstanding_ar"] += remaining
                per_customer[cid]["open_count"] += 1
                if invoice_date and due_date:
                    per_customer[cid]["collection_days_total"] += (due_date - invoice_date).days
                    per_customer[cid]["collection_count"] += 1

        # Build top_inflows using customer metadata and invoice aggregates
        top_inflows = []
        for c in customers:
            cid = c.get("customer_id") or c.get("customerId") or c.get("id")
            agg = per_customer.get(cid, {})
            if agg.get("outstanding_ar", 0) <= 0:
                continue
            avg_collection_days = None
            if agg.get("collection_count"):
                avg_collection_days = agg["collection_days_total"] / agg["collection_count"]
            expected_date = (datetime.now() + timedelta(days=int(avg_collection_days or 30))).strftime('%Y-%m-%d')

            top_inflows.append({
                'source': c.get("customer_name") or c.get("name") or c.get("customerName"),
                'customer_id': int(cid) if cid is not None else None,
                'amount': round(float(agg.get("outstanding_ar", 0.0)), 2),
                'open_invoices': int(agg.get("open_count", 0)),
                'expected_collection_date': expected_date,
                'collection_probability': float(c.get("payment_reliability_score") or c.get("reliability") or 0.0)
            })

        # Sort and limit
        top_inflows = sorted(top_inflows, key=lambda x: x['amount'], reverse=True)[:5]

        # Aggregate bills by expense_category for outflows
        outflow_map = {}
        for b in bills:
            category = b.get("expense_category") or b.get("category") or "other"
            status = (b.get("payment_status") or b.get("status") or "").lower()
            amount = b.get("amount") or 0
            try:
                amount = float(amount)
            except Exception:
                try:
                    amount = float(str(amount).replace(",", ""))
                except Exception:
                    amount = 0.0
            if status != "open":
                continue
            if category not in outflow_map:
                outflow_map[category] = {
                    "total_amount": 0.0,
                    "count": 0,
                    "earliest_due": None
                }
            outflow_map[category]["total_amount"] += amount
            outflow_map[category]["count"] += 1
            due = self._safe_date_parse(b.get("due_date") or b.get("dueDate"))
            if due:
                current = outflow_map[category]["earliest_due"]
                if current is None or due < current:
                    outflow_map[category]["earliest_due"] = due

        top_outflows = []
        for cat, v in outflow_map.items():
            top_outflows.append({
                'type': cat,
                'amount': round(float(v["total_amount"]), 2),
                'bill_count': int(v["count"]),
                'earliest_due': v["earliest_due"].strftime('%Y-%m-%d') if v["earliest_due"] else None
            })

        top_outflows = sorted(top_outflows, key=lambda x: x['amount'], reverse=True)[:5]

        state['drivers'] = {
            'top_inflows': top_inflows,
            'top_outflows': top_outflows
        }

        state['current_step'] = 'drivers_identified'

        logger.info(f"[{self.agent_id}] Identified {len(top_inflows)} inflows, {len(top_outflows)} outflows")

        return state
    
    # ============================================================
    # STEP 7: Prepare Output
    # ============================================================

    async def prepare_output(self, state: Dict) -> Dict:
        """Prepare final output"""
        logger.info(f"[{self.agent_id}] Step 7: Preparing output")

        if state.get('error'):
            return state

        forecast_list = state.get('forecast_results') or []
        drivers = state.get('drivers', {})
        model_info = state.get('model_info') or {}

        # safe summary fields (handle empty forecasts)
        forecast_start = forecast_list[0]['date'] if forecast_list else None
        forecast_end = forecast_list[-1]['date'] if forecast_list else None
        current_balance = forecast_list[0]['predicted_balance'] if forecast_list else None
        ending_balance = forecast_list[-1]['predicted_balance'] if forecast_list else None
        min_balance = min((f['predicted_balance'] for f in forecast_list), default=None)
        max_balance = max((f['predicted_balance'] for f in forecast_list), default=None)
        model_accuracy_mape = model_info.get('mape') if isinstance(model_info, dict) else None

        state['output'] = {
            'status': 'success',
            'agent_id': self.agent_id,
            'timestamp': datetime.now().isoformat(),
            'forecast': forecast_list,
            'drivers': drivers,
            'model_info': model_info,
            'summary': {
                'forecast_days': 91,
                'forecast_start': forecast_start,
                'forecast_end': forecast_end,
                'current_balance': current_balance,
                'ending_balance': ending_balance,
                'min_balance': min_balance,
                'max_balance': max_balance,
                'model_accuracy_mape': model_accuracy_mape
            }
        }

        state['current_step'] = 'complete'

        logger.info(f"[{self.agent_id}] Forecast complete")

        return state
# ============================================================
# FastAPI Integration
# ============================================================

async def run_forecasting_agent(org_id: int) -> Dict[str, Any]:
    """Execute forecasting agent"""
    agent = ForecastingAgent()
    graph = await agent.create_graph()
    
    state = {
        'org_id': org_id,
        'current_step': 'initialized'
    }
    
    result = await graph.invoke(state)
    return result.get('output', {})
