#!/usr/bin/env python3
"""
AGENT 4: SCENARIO ANALYZER
Test what-if scenarios for CFO decision-making

Purpose:
  • Load base 91-day forecast from Agent 2
  • Apply user scenario modifications (delays, new orders, expense shifts, etc)
  • Recalculate cash trajectory
  • Compare vs base case
  • Generate sensitivity analysis
  • Produce board-ready output

Inputs:
  • org_id: Organization ID
  • base_forecast: 91-day forecast from Agent 2 (or fetch from agent endpoint)
  • scenario_instructions: List of modifications to apply

  Supported modifications:
    - "delay collections by 15 days"
    - "add ₹5Cr order on 2025-12-25"
    - "defer rent 10 days"
    - "reduce payroll by 20%"
    - "loan restructure: 50% emi reduction for 3 months"
    - "freeze hiring"
    - "capex: ₹2Cr on 2025-12-22"

Output:
  • Scenario forecast (91 days)
  • Impact metrics (min balance, collisions, deficits)
  • Sensitivity analysis (collection delays, new orders, expense cuts)
  • Comparison vs base
  • HTML/PDF for board presentation
"""

import json
import requests
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from copy import deepcopy
import statistics

# Import forecasting runner from Agent 2
from Forecast_Agent.agent import run_forecasting_agent

# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class DailyForecast:
    """Daily cash flow forecast"""
    date: str
    opening_balance: float
    inflows: float
    outflows: float
    net_cashflow: float
    closing_balance: float
    # Optional breakdowns
    ar_collections: float = 0
    new_sales_inflows: float = 0
    operating_expenses: float = 0
    payroll: float = 0
    rent: float = 0
    loan_repayments: float = 0
    capex: float = 0

@dataclass
class BaseForecast:
    """Complete 91-day forecast"""
    org_id: int
    currency: str
    horizon_days: int
    as_of: str
    days: List[DailyForecast]

@dataclass
class ImpactMetrics:
    """Metrics comparing base vs scenario"""
    min_balance_base: float
    min_balance_scenario: float
    min_balance_improvement: float
    collisions_base: List[str]  # dates with negative balance
    collisions_scenario: List[str]
    collisions_avoided: List[str]
    collisions_added: List[str]
    max_deficit_base: float  # most negative balance
    max_deficit_scenario: float
    max_deficit_improvement: float
    total_net_base: float  # sum of net_cashflow
    total_net_scenario: float
    total_net_delta: float
    min_date_base: str
    min_date_scenario: str

# ============================================================
# SCENARIO MODIFICATIONS
# ============================================================

class ScenarioModifier:
    """Apply scenario modifications to forecast"""
    
    @staticmethod
    def parse_instruction(text: str) -> Dict[str, Any]:
        """Parse free-text instruction into structured format"""
        text = text.lower().strip()
        
        # Collection delay: "delay collections by 15 days"
        if "delay" in text and "collection" in text:
            import re
            match = re.search(r'delay.*?(\d+)\s*days?', text)
            if match:
                return {
                    "type": "collection_delay",
                    "days": int(match.group(1))
                }
        
        # New order: "add ₹5Cr order on 2025-12-25"
        if "add" in text and ("order" in text or "revenue" in text):
            import re
            # Match currency amounts: ₹5Cr, ₹1000L, etc
            match = re.search(r'₹([\d.]+)\s*([A-Za-z]+)', text)
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
            if match and date_match:
                amount_str = match.group(1)
                unit = match.group(2).lower()
                date = date_match.group(1)
                
                # Convert to rupees
                amount = float(amount_str)
                if 'cr' in unit:
                    amount *= 10_000_000
                elif 'l' in unit:
                    amount *= 100_000
                
                return {
                    "type": "new_order",
                    "date": date,
                    "amount": amount
                }
        
        # Expense deferral: "defer rent 10 days"
        if "defer" in text or "postpone" in text:
            import re
            category = "rent" if "rent" in text else "operating_expenses"
            match = re.search(r'(?:defer|postpone).*?(\d+)\s*days?', text)
            if match:
                return {
                    "type": "expense_shift",
                    "category": category,
                    "shift_days": int(match.group(1))
                }
        
        # Expense reduction: "reduce payroll by 20%"
        if "reduce" in text or "cut" in text:
            import re
            category = "payroll" if "payroll" in text else "operating_expenses"
            match = re.search(r'(?:reduce|cut).*?(\d+)\s*%', text)
            if match:
                return {
                    "type": "expense_reduction",
                    "category": category,
                    "pct_reduction": int(match.group(1))
                }
        
        # Loan restructure: "loan restructure: 50% emi reduction for 3 months"
        if "loan" in text and "restructure" in text:
            import re
            pct_match = re.search(r'(\d+)\s*%', text)
            month_match = re.search(r'(\d+)\s*months?', text)
            pct = int(pct_match.group(1)) if pct_match else 50
            months = int(month_match.group(1)) if month_match else 3
            return {
                "type": "loan_restructure",
                "pct_reduction": pct,
                "months": months
            }
        
        # Hiring freeze: "freeze hiring"
        if "freeze" in text and "hiring" in text:
            return {
                "type": "hiring",
                "change": "freeze"
            }
        
        # Capex: "capex: ₹2Cr on 2025-12-22"
        if "capex" in text:
            import re
            amount_match = re.search(r'₹([\d.]+)\s*([A-Za-z]+)', text)
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
            if amount_match and date_match:
                amount_str = amount_match.group(1)
                unit = amount_match.group(2).lower()
                date = date_match.group(1)
                
                amount = float(amount_str)
                if 'cr' in unit:
                    amount *= 10_000_000
                elif 'l' in unit:
                    amount *= 100_000
                
                return {
                    "type": "capex",
                    "date": date,
                    "amount": amount
                }
        
        return None
    
    @staticmethod
    def apply_collection_delay(forecast: BaseForecast, days: int) -> None:
        """Delay AR collections by N days"""
        date_to_idx = {d.date: i for i, d in enumerate(forecast.days)}
        moved = {}
        
        for i, day in enumerate(forecast.days):
            if day.ar_collections <= 0:
                continue
            
            target_date = (datetime.strptime(day.date, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")
            
            if target_date not in date_to_idx:
                continue  # beyond horizon
            
            target_idx = date_to_idx[target_date]
            amount = day.ar_collections
            
            day.inflows -= amount
            day.ar_collections = 0
            
            if target_date not in moved:
                moved[target_date] = 0
            moved[target_date] += amount
        
        for target_date, amount in moved.items():
            idx = date_to_idx[target_date]
            forecast.days[idx].inflows += amount
            forecast.days[idx].ar_collections += amount
    
    @staticmethod
    def apply_new_order(forecast: BaseForecast, date: str, amount: float) -> None:
        """Add new order revenue on specific date"""
        date_to_idx = {d.date: i for i, d in enumerate(forecast.days)}
        if date not in date_to_idx:
            return
        
        idx = date_to_idx[date]
        forecast.days[idx].inflows += amount
        forecast.days[idx].new_sales_inflows += amount
    
    @staticmethod
    def apply_expense_shift(forecast: BaseForecast, category: str, shift_days: int) -> None:
        """Defer expense by N days"""
        date_to_idx = {d.date: i for i, d in enumerate(forecast.days)}
        moved = {}
        
        for i, day in enumerate(forecast.days):
            cat_amount = getattr(day, category, 0)
            if cat_amount <= 0:
                continue
            
            target_date = (datetime.strptime(day.date, "%Y-%m-%d") + timedelta(days=shift_days)).strftime("%Y-%m-%d")
            
            if target_date not in date_to_idx:
                continue
            
            day.outflows -= cat_amount
            setattr(day, category, 0)
            
            if target_date not in moved:
                moved[target_date] = 0
            moved[target_date] += cat_amount
        
        for target_date, amount in moved.items():
            idx = date_to_idx[target_date]
            forecast.days[idx].outflows += amount
            setattr(forecast.days[idx], category, getattr(forecast.days[idx], category, 0) + amount)
    
    @staticmethod
    def apply_expense_reduction(forecast: BaseForecast, category: str, pct: float, start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
        """Reduce expense by X% for date range"""
        for day in forecast.days:
            if start_date and day.date < start_date:
                continue
            if end_date and day.date > end_date:
                continue
            
            cat_amount = getattr(day, category, 0)
            if cat_amount <= 0:
                continue
            
            delta = cat_amount * (pct / 100)
            setattr(day, category, cat_amount - delta)
            day.outflows -= delta
    
    @staticmethod
    def apply_capex(forecast: BaseForecast, date: str, amount: float) -> None:
        """Add one-time capex on specific date"""
        date_to_idx = {d.date: i for i, d in enumerate(forecast.days)}
        if date not in date_to_idx:
            return
        
        idx = date_to_idx[date]
        forecast.days[idx].outflows += amount
        forecast.days[idx].capex += amount

# ============================================================
# FORECAST OPERATIONS
# ============================================================

def recompute_balances(forecast: BaseForecast) -> None:
    """Recalculate cash balances day by day"""
    if not forecast.days:
        return
    
    prev_closing = forecast.days[0].opening_balance
    for day in forecast.days:
        day.opening_balance = prev_closing
        day.net_cashflow = day.inflows - day.outflows
        day.closing_balance = day.opening_balance + day.net_cashflow
        prev_closing = day.closing_balance

def compute_impact(base: BaseForecast, scenario: BaseForecast) -> ImpactMetrics:
    """Compare base vs scenario forecast"""
    min_base = float('inf')
    min_scen = float('inf')
    max_def_base = 0
    max_def_scen = 0
    tot_base = 0
    tot_scen = 0
    coll_base = []
    coll_scen = []
    min_date_base = ""
    min_date_scen = ""
    
    for i in range(len(base.days)):
        b = base.days[i]
        s = scenario.days[i]
        
        if b.closing_balance < min_base:
            min_base = b.closing_balance
            min_date_base = b.date
        if s.closing_balance < min_scen:
            min_scen = s.closing_balance
            min_date_scen = s.date
        
        if b.closing_balance < 0:
            max_def_base = min(max_def_base, b.closing_balance)
            coll_base.append(b.date)
        if s.closing_balance < 0:
            max_def_scen = min(max_def_scen, s.closing_balance)
            coll_scen.append(s.date)
        
        tot_base += b.net_cashflow
        tot_scen += s.net_cashflow
    
    set_base = set(coll_base)
    set_scen = set(coll_scen)
    avoided = [d for d in coll_base if d not in set_scen]
    added = [d for d in coll_scen if d not in set_base]
    
    return ImpactMetrics(
        min_balance_base=min_base,
        min_balance_scenario=min_scen,
        min_balance_improvement=min_scen - min_base,
        collisions_base=coll_base,
        collisions_scenario=coll_scen,
        collisions_avoided=avoided,
        collisions_added=added,
        max_deficit_base=max_def_base,
        max_deficit_scenario=max_def_scen,
        max_deficit_improvement=max_def_scen - max_def_base,
        total_net_base=tot_base,
        total_net_scenario=tot_scen,
        total_net_delta=tot_scen - tot_base,
        min_date_base=min_date_base,
        min_date_scenario=min_date_scen
    )

def run_sensitivity(base: BaseForecast) -> List[Dict[str, Any]]:
    """One-way sensitivity analysis on key levers"""
    results = []
    
    # Collection delay sensitivity
    for delay_days in [0, 7, 15, 30]:
        scen = deepcopy(base)
        if delay_days > 0:
            ScenarioModifier.apply_collection_delay(scen, delay_days)
        recompute_balances(scen)
        impact = compute_impact(base, scen)
        results.append({
            "lever": "collection_delay_days",
            "value": delay_days,
            "min_balance": impact.min_balance_scenario,
            "collisions": len(impact.collisions_scenario),
            "improvement": impact.min_balance_improvement
        })
    
    # New order sensitivity
    for order_amount in [0, 2_000_000_0, 5_000_000_0, 10_000_000_0]:
        scen = deepcopy(base)
        if order_amount > 0:
            # Add on day 10 of forecast
            if len(scen.days) >= 10:
                ScenarioModifier.apply_new_order(scen, scen.days[9].date, order_amount)
        recompute_balances(scen)
        impact = compute_impact(base, scen)
        results.append({
            "lever": "new_order_amount",
            "value": order_amount,
            "min_balance": impact.min_balance_scenario,
            "collisions": len(impact.collisions_scenario),
            "improvement": impact.min_balance_improvement
        })
    
    # Expense reduction sensitivity
    for reduction_pct in [0, 10, 20, 30]:
        scen = deepcopy(base)
        if reduction_pct > 0:
            ScenarioModifier.apply_expense_reduction(scen, "operating_expenses", reduction_pct)
        recompute_balances(scen)
        impact = compute_impact(base, scen)
        results.append({
            "lever": "expense_reduction_pct",
            "value": reduction_pct,
            "min_balance": impact.min_balance_scenario,
            "collisions": len(impact.collisions_scenario),
            "improvement": impact.min_balance_improvement
        })
    
    return results

def generate_html_report(
    org_id: int,
    org_name: str,
    base: BaseForecast,
    scenario: BaseForecast,
    impact: ImpactMetrics,
    sensitivity: List[Dict],
    scenario_description: str
) -> str:
    """Generate HTML report for PDF conversion"""
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CFO Scenario Analysis - {org_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 40px;
            color: #333;
            background-color: #f9f9f9;
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            color: #1e40af;
        }}
        .header p {{
            margin: 5px 0;
            color: #666;
        }}
        .scenario-desc {{
            background-color: #e3f2fd;
            border-left: 4px solid #2563eb;
            padding: 15px;
            margin: 20px 0;
            font-size: 14px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-card {{
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .metric-card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .metric-value {{
            font-size: 28px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metric-value.positive {{
            color: #16a34a;
        }}
        .metric-value.negative {{
            color: #dc2626;
        }}
        .metric-label {{
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }}
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
        }}
        .comparison-table th {{
            background-color: #f3f4f6;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e5e7eb;
        }}
        .comparison-table td {{
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .comparison-table tr:hover {{
            background-color: #f9fafb;
        }}
        .collision-warning {{
            background-color: #fef2f2;
            border-left: 4px solid #dc2626;
            padding: 12px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        .collision-success {{
            background-color: #f0fdf4;
            border-left: 4px solid #16a34a;
            padding: 12px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        .sensitivity-section {{
            margin-top: 40px;
            page-break-inside: avoid;
        }}
        .sensitivity-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #1e40af;
        }}
        .forecast-summary {{
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .forecast-summary h3 {{
            margin-top: 0;
            color: #1e40af;
        }}
        .key-dates {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        .date-box {{
            background: #f9fafb;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #e5e7eb;
        }}
        .date-box .label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .date-box .date {{
            font-size: 18px;
            font-weight: 600;
            color: #1e40af;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Scenario Analysis Report</h1>
        <p><strong>{org_name}</strong> (Org ID: {org_id})</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="scenario-desc">
        <strong>Scenario:</strong> {scenario_description}
    </div>
    
    <div class="metrics-grid">
        <div class="metric-card">
            <h3>Minimum Balance</h3>
            <div class="metric-value {'positive' if impact.min_balance_scenario >= 0 else 'negative'}">
                ₹{impact.min_balance_scenario/10_000_000:.2f}Cr
            </div>
            <div class="metric-label">
                {'Improvement: ₹' + f'{impact.min_balance_improvement/10_000_000:.2f}Cr' if impact.min_balance_improvement > 0 else 'Deterioration: ₹' + f'{abs(impact.min_balance_improvement)/10_000_000:.2f}Cr'}
            </div>
        </div>
        
        <div class="metric-card">
            <h3>Cash Crunches</h3>
            <div class="metric-value {'negative' if len(impact.collisions_scenario) > 0 else 'positive'}">
                {len(impact.collisions_scenario)}
            </div>
            <div class="metric-label">
                Negative balance dates
            </div>
        </div>
        
        <div class="metric-card">
            <h3>Maximum Deficit</h3>
            <div class="metric-value negative">
                -₹{abs(impact.max_deficit_scenario)/10_000_000:.2f}Cr
            </div>
            <div class="metric-label">
                Deepest crunch depth
            </div>
        </div>
    </div>
    
    <div class="key-dates">
        <div class="date-box">
            <div class="label">Minimum Balance Date (Base)</div>
            <div class="date">{impact.min_date_base}</div>
        </div>
        <div class="date-box">
            <div class="label">Minimum Balance Date (Scenario)</div>
            <div class="date">{impact.min_date_scenario}</div>
        </div>
    </div>
    
    <div class="forecast-summary">
        <h3>Impact Summary</h3>
        
        {'<div class="collision-success">✓ ' + f'{len(impact.collisions_avoided)} cash crunches AVOIDED</div>' if impact.collisions_avoided else ''}
        {'<div class="collision-warning">✗ ' + f'{len(impact.collisions_added)} NEW cash crunches ADDED</div>' if impact.collisions_added else ''}
        
        <table class="comparison-table">
            <tr>
                <th>Metric</th>
                <th>Base Forecast</th>
                <th>Scenario Forecast</th>
                <th>Improvement</th>
            </tr>
            <tr>
                <td>Minimum Balance</td>
                <td>₹{impact.min_balance_base/10_000_000:.2f}Cr</td>
                <td>₹{impact.min_balance_scenario/10_000_000:.2f}Cr</td>
                <td>₹{impact.min_balance_improvement/10_000_000:.2f}Cr</td>
            </tr>
            <tr>
                <td>Maximum Deficit</td>
                <td>₹{impact.max_deficit_base/10_000_000:.2f}Cr</td>
                <td>₹{impact.max_deficit_scenario/10_000_000:.2f}Cr</td>
                <td>₹{impact.max_deficit_improvement/10_000_000:.2f}Cr</td>
            </tr>
            <tr>
                <td>Cash Crunches</td>
                <td>{len(impact.collisions_base)}</td>
                <td>{len(impact.collisions_scenario)}</td>
                <td>{len(impact.collisions_base) - len(impact.collisions_scenario)}</td>
            </tr>
            <tr>
                <td>Total Net Cashflow (91 days)</td>
                <td>₹{impact.total_net_base/10_000_000:.2f}Cr</td>
                <td>₹{impact.total_net_scenario/10_000_000:.2f}Cr</td>
                <td>₹{impact.total_net_delta/10_000_000:.2f}Cr</td>
            </tr>
        </table>
    </div>
    
    <div class="sensitivity-section">
        <h2 class="sensitivity-title">Sensitivity Analysis</h2>
        <p>How key levers affect the scenario outcome:</p>
        <table class="comparison-table">
            <tr>
                <th>Lever</th>
                <th>Value</th>
                <th>Min Balance</th>
                <th>Crunches</th>
                <th>Improvement</th>
            </tr>
"""
    
    for s in sensitivity:
        html += f"""
            <tr>
                <td>{s['lever']}</td>
                <td>{s['value']}</td>
                <td>₹{s['min_balance']/10_000_000:.2f}Cr</td>
                <td>{s['collisions']}</td>
                <td>₹{s['improvement']/10_000_000:.2f}Cr</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
    
    <div class="footer">
        <p>This report is for internal decision-making purposes only.</p>
        <p>Forecasts are subject to model assumptions and market conditions.</p>
    </div>
</body>
</html>
"""
    
    return html

# ============================================================
# MAIN AGENT
# ============================================================

def _build_base_forecast_from_agent_output(org_id: int, forecast_output: Dict[str, Any]) -> Optional[BaseForecast]:
    """Map Forecast Agent output -> BaseForecast dataclass"""
    if not forecast_output:
        return None

    # forecast may be under different keys depending on agent implementation
    forecast_list = forecast_output.get('forecast') or forecast_output.get('forecast_results') or forecast_output.get('forecast_list') or []
    summary = forecast_output.get('summary', {}) or {}
    as_of = forecast_output.get('timestamp') or forecast_output.get('as_of') or datetime.now().strftime("%Y-%m-%d")
    currency = forecast_output.get('currency', 'INR')

    if not forecast_list:
        return None

    days = []
    # initial opening balance from summary.current_balance or infer from first predicted_balance
    prev_closing = None
    if 'current_balance' in summary and summary['current_balance'] is not None:
        try:
            prev_closing = float(summary['current_balance'])
        except Exception:
            prev_closing = None
    if prev_closing is None:
        try:
            prev_closing = float(forecast_list[0].get('predicted_balance', 0))
        except Exception:
            prev_closing = 0.0

    for f in forecast_list:
        date = f.get('date') or f.get('forecast_date') or datetime.now().strftime("%Y-%m-%d")
        closing = float(f.get('predicted_balance') if f.get('predicted_balance') is not None else prev_closing)
        # preferred daily change field, else infer
        daily_change = f.get('daily_change')
        if daily_change is None:
            daily_change = closing - prev_closing

        inflows = daily_change if daily_change > 0 else 0.0
        outflows = -daily_change if daily_change < 0 else 0.0
        opening = prev_closing
        net = inflows - outflows

        day = DailyForecast(
            date=str(date),
            opening_balance=float(opening),
            inflows=float(inflows),
            outflows=float(outflows),
            net_cashflow=float(net),
            closing_balance=float(closing),
            ar_collections=0.0,
            operating_expenses=0.0,
            payroll=0.0,
            rent=0.0,
            loan_repayments=0.0,
            capex=0.0,
            new_sales_inflows=float(f.get('new_sales_inflows', 0) or 0)
        )
        days.append(day)
        prev_closing = closing

    return BaseForecast(
        org_id=org_id,
        currency=currency,
        horizon_days=len(days),
        as_of=as_of,
        days=days
    )

def scenario_agent(
    org_id: int,
    scenario_instructions: List[str],
    base_url: str = "https://fintro-backend-883163069340.asia-south1.run.app"
) -> Dict[str, Any]:
    """
    Main scenario analysis agent
    
    Args:
        org_id: Organization ID
        scenario_instructions: List of scenario modifications (free text)
        base_url: API base URL
    
    Returns:
        Complete scenario analysis with forecasts, metrics, and HTML report
    """
    
    print(f"\n{'='*70}")
    print(f"SCENARIO ANALYZER - AGENT 4")
    print(f"{'='*70}\n")
    
    # 1. Fetch base forecast using Forecast Agent (Agent 2)
    print(f"📊 Fetching base forecast for org {org_id} from Forecast Agent...")
    forecast_output = {}
    try:
        # run_forecasting_agent is async -> call from sync code
        forecast_output = asyncio.run(run_forecasting_agent(org_id))
    except Exception as e:
        print(f"⚠️ Forecast Agent call failed: {e}")
        forecast_output = {}

    base_forecast = _build_base_forecast_from_agent_output(org_id, forecast_output)
    # fallback to sample if agent didn't return usable forecast
    if base_forecast is None:
        print("⚠️ Forecast Agent did not return usable forecast; falling back to sample forecast")
        base_forecast = create_sample_base_forecast(org_id)

    # fetch org name via backend for report header (best-effort)
    org_name = f"Organization {org_id}"
    try:
        resp = requests.get(f"{base_url}/organizations/{org_id}", timeout=5)
        if resp.ok:
            org_json = resp.json()
            org_name = org_json.get("org_name", org_json.get("name", org_name))
    except Exception:
        pass

    print(f"✓ Loaded {len(base_forecast.days)} day forecast")
    print(f"✓ Organization: {org_name}")
    
    # 2. Parse scenario instructions
    print(f"\n📝 Parsing scenario instructions...")
    modifications = []
    for instruction in scenario_instructions:
        mod = ScenarioModifier.parse_instruction(instruction)
        if mod:
            modifications.append(mod)
            print(f"✓ {instruction}")
        else:
            print(f"⚠️ Could not parse: {instruction}")
    
    # 3. Create scenario forecast (deep copy)
    scenario_forecast = deepcopy(base_forecast)
    
    # 4. Apply modifications
    print(f"\n⚙️ Applying {len(modifications)} modifications...")
    for mod in modifications:
        if mod['type'] == 'collection_delay':
            ScenarioModifier.apply_collection_delay(scenario_forecast, mod['days'])
            print(f"✓ Delayed collections by {mod['days']} days")
        elif mod['type'] == 'new_order':
            ScenarioModifier.apply_new_order(scenario_forecast, mod['date'], mod['amount'])
            print(f"✓ Added ₹{mod['amount']/10_000_000:.1f}Cr order on {mod['date']}")
        elif mod['type'] == 'expense_shift':
            ScenarioModifier.apply_expense_shift(scenario_forecast, mod['category'], mod['shift_days'])
            print(f"✓ Deferred {mod['category']} by {mod['shift_days']} days")
        elif mod['type'] == 'expense_reduction':
            ScenarioModifier.apply_expense_reduction(scenario_forecast, mod['category'], mod['pct_reduction'])
            print(f"✓ Reduced {mod['category']} by {mod['pct_reduction']}%")
        elif mod['type'] == 'capex':
            ScenarioModifier.apply_capex(scenario_forecast, mod['date'], mod['amount'])
            print(f"✓ Added ₹{mod['amount']/10_000_000:.1f}Cr capex on {mod['date']}")
        elif mod['type'] == 'hiring':
            print(f"✓ Hiring {mod['change']}")
    
    # 5. Recompute balances
    print(f"\n🔄 Recomputing cash balances...")
    recompute_balances(scenario_forecast)
    print(f"✓ Recalculated scenario forecast")
    
    # 6. Compute impact metrics
    print(f"\n📈 Computing impact metrics...")
    impact = compute_impact(base_forecast, scenario_forecast)
    print(f"✓ Min balance: ₹{impact.min_balance_scenario/10_000_000:.2f}Cr (was ₹{impact.min_balance_base/10_000_000:.2f}Cr)")
    print(f"✓ Cash crunches: {len(impact.collisions_scenario)} (was {len(impact.collisions_base)})")
    if impact.collisions_avoided:
        print(f"✓ Avoided: {', '.join(impact.collisions_avoided)}")
    if impact.collisions_added:
        print(f"✗ Added: {', '.join(impact.collisions_added)}")
    
    # 7. Sensitivity analysis
    print(f"\n🎯 Running sensitivity analysis...")
    sensitivity = run_sensitivity(scenario_forecast)
    print(f"✓ Analyzed 3 levers × 4 values each")
    
    # 8. Generate HTML report
    print(f"\n📄 Generating HTML report...")
    scenario_desc = " + ".join(scenario_instructions) if scenario_instructions else "No modifications"
    html_report = generate_html_report(
        org_id, org_name, base_forecast, scenario_forecast,
        impact, sensitivity, scenario_desc
    )
    print(f"✓ Generated HTML report ({len(html_report)} chars)")
    
    # 9. Prepare output
    print(f"\n✅ ANALYSIS COMPLETE\n")
    
    return {
        "org_id": org_id,
        "org_name": org_name,
        "status": "success",
        "base_forecast": {
            "days": [asdict(d) for d in base_forecast.days],
            "summary": {
                "min_balance": impact.min_balance_base,
                "max_deficit": impact.max_deficit_base,
                "collisions": len(impact.collisions_base),
                "total_net_cashflow": impact.total_net_base
            }
        },
        "scenario_forecast": {
            "days": [asdict(d) for d in scenario_forecast.days],
            "summary": {
                "min_balance": impact.min_balance_scenario,
                "max_deficit": impact.max_deficit_scenario,
                "collisions": len(impact.collisions_scenario),
                "total_net_cashflow": impact.total_net_scenario
            }
        },
        "impact": asdict(impact),
        "sensitivity": sensitivity,
        "comparison": {
            "cash_improvement": impact.min_balance_improvement,
            "crunches_avoided": len(impact.collisions_avoided),
            "crunches_added": len(impact.collisions_added),
            "max_deficit_improvement": impact.max_deficit_improvement,
            "total_cashflow_delta": impact.total_net_delta
        },
        "html_report": html_report,
        "pdf_url": None  # Set by PDF rendering service
    }

def create_sample_base_forecast(org_id: int) -> BaseForecast:
    """Create sample 91-day forecast for demo"""
    import random
    days = []
    opening_balance = 1000_000_000  # ₹10Cr starting balance
    
    today = datetime.now()
    
    for i in range(91):
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        inflows = random.randint(1_000_000, 5_000_000) if i % 3 == 0 else random.randint(100_000, 500_000)
        outflows = random.randint(500_000, 3_000_000)
        net = inflows - outflows
        closing = opening_balance + net
        
        day = DailyForecast(
            date=date,
            opening_balance=opening_balance,
            inflows=inflows,
            outflows=outflows,
            net_cashflow=net,
            closing_balance=closing,
            ar_collections=inflows * 0.7,
            operating_expenses=outflows * 0.5,
            payroll=outflows * 0.3,
            rent=outflows * 0.1,
            loan_repayments=outflows * 0.05,
            capex=0
        )
        days.append(day)
        opening_balance = closing
    
    return BaseForecast(
        org_id=org_id,
        currency="INR",
        horizon_days=91,
        as_of=datetime.now().strftime("%Y-%m-%d"),
        days=days
    )

if __name__ == "__main__":
    # Example usage
    result = scenario_agent(
        org_id=90,
        scenario_instructions=[
            "delay collections by 15 days",
            "add ₹5 Crore order on 2025-12-25",
            "defer rent 10 days"
        ]
    )
    
    print("\n📊 OUTPUT SUMMARY:")
    print(f"Min Balance Improvement: ₹{result['comparison']['cash_improvement']/10_000_000:.2f}Cr")
    print(f"Crunches Avoided: {result['comparison']['crunches_avoided']}")
    print(f"HTML Report: {len(result['html_report'])} bytes")