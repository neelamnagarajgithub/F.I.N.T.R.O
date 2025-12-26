"""
Agent 4: Liquidity & Collision Detection
Predicts cash crunches and suggests mitigation strategies
"""

from langgraph.graph import StateGraph, START, END
from typing import Dict, Any, List, Tuple
import logging
import httpx
from datetime import date, datetime, timedelta
import statistics
from Forecast_Agent.agent import run_forecasting_agent

logger = logging.getLogger(__name__)

class CollisionAgent:
    """
    Agent 4: Collision Detection
    Predicts when cash goes negative and recommends mitigation
    """
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
        self.agent_id = "agent_4_collision_detection"
        self.client = httpx.AsyncClient(base_url=backend_url, timeout=30.0)
    
    def _parse_date(self, s):
        """Parse various date formats into a datetime.date or return None."""
        if not s:
            return None
        # if already a date/datetime
        try:
            if isinstance(s, datetime):
                return s.date()
        except Exception:
            pass
        try:
            s = str(s)
            # Common ISO with time e.g. 2025-12-20T06:06:04.420Z -> take date part
            if 'T' in s:
                s = s.split('T')[0]
            # Trim timezone Z if present
            s = s.rstrip('Z')
            return datetime.strptime(s[:10], '%Y-%m-%d').date()
        except Exception:
            # last resort: try fromisoformat after replacing Z
            try:
                s2 = str(s).replace('Z', '+00:00')
                return datetime.fromisoformat(s2).date()
            except Exception:
                return None

    def _to_float(self, v, default=0.0):
        """Safely convert values to float (handles strings with commas/currency)."""
        try:
            if v is None:
                return float(default)
            if isinstance(v, (int, float)):
                return float(v)
            s = str(v).strip()
            if s == "":
                return float(default)
            # Remove common currency symbols and thousands separators
            s = s.replace(",", "").replace("₹", "").replace("$", "")
            # If there are parentheses for negatives e.g. (1,000)
            if s.startswith("(") and s.endswith(")"):
                s = "-" + s[1:-1]
            return float(s)
        except Exception:
            return float(default)

    async def create_graph(self):
        """Create LangGraph workflow"""
        workflow = StateGraph(Dict[str, Any])
        
        # Define nodes
        workflow.add_node("get_current_balance", self.get_current_balance)
        workflow.add_node("get_forecast", self.get_forecast)
        workflow.add_node("get_mandatory_expenses", self.get_mandatory_expenses)
        workflow.add_node("get_credit_limits", self.get_credit_limits)
        workflow.add_node("detect_collisions", self.detect_collisions)
        workflow.add_node("analyze_severity", self.analyze_severity)
        workflow.add_node("generate_mitigation", self.generate_mitigation)
        workflow.add_node("prepare_output", self.prepare_output)
        
        # Define edges
        workflow.add_edge(START, "get_current_balance")
        workflow.add_edge("get_current_balance", "get_forecast")
        workflow.add_edge("get_forecast", "get_mandatory_expenses")
        workflow.add_edge("get_mandatory_expenses", "get_credit_limits")
        workflow.add_edge("get_credit_limits", "detect_collisions")
        workflow.add_edge("detect_collisions", "analyze_severity")
        workflow.add_edge("analyze_severity", "generate_mitigation")
        workflow.add_edge("generate_mitigation", "prepare_output")
        workflow.add_edge("prepare_output", END)
        
        return workflow.compile()
    
    async def get_current_balance(self, state: Dict) -> Dict:
        """Fetch opening balance and compute current balance = opening + inflows - outflows"""
        logger.info(f"[{self.agent_id}] Fetching current balance (recomputed from opening + inflows - outflows)")

        org_id = state['org_id']
        today = datetime.now().date()

        try:
            # Get org summary (contains opening_balance if available)
            org_response = await self.client.get(f"/organizations/{org_id}/summary")
            org_data = org_response.json()

            opening_balance = float(org_data.get('opening_balance', org_data.get('current_balance', 0)))
            minimum_balance = float(org_data.get('minimum_balance_required', 500000))

            # Fetch payments up to today to compute inflows/outflows
            payments_resp = await self.client.get(
                f"/payments/org/{org_id}",
                params={"to": today.strftime('%Y-%m-%d')}
            )
            payments = payments_resp.json().get('payments', []) if payments_resp is not None else []

            inflows = 0.0
            outflows = 0.0
            for p in payments:
                try:
                    amt = float(p.get('payment_amount', p.get('amount', 0)) or 0)
                except Exception:
                    try:
                        amt = float(str(p.get('payment_amount', 0)).replace(',', ''))
                    except Exception:
                        amt = 0.0
                ptype = (p.get('payment_type') or p.get('type') or '').lower()
                if ptype == 'inflow':
                    inflows += amt
                elif ptype == 'outflow':
                    outflows += amt
                else:
                    # default: treat positive as inflow
                    inflows += amt

            current_balance = opening_balance + inflows - outflows

            state['opening_balance'] = opening_balance
            state['current_balance'] = float(current_balance)
            state['minimum_balance'] = minimum_balance
            state['balance_gap'] = float(current_balance) - minimum_balance
            state['recent_inflows'] = inflows
            state['recent_outflows'] = outflows
            state['current_step'] = 'balance_fetched'

            logger.info(f"Opening: ₹{opening_balance:,.2f}  Inflows: ₹{inflows:,.2f}  Outflows: ₹{outflows:,.2f}  Current: ₹{current_balance:,.2f}")

        except Exception as e:
            logger.error(f"Error fetching current balance: {e}")
            state['error'] = str(e)

        return state

    async def get_forecast(self, state: Dict) -> Dict:
        """Obtain 91-day forecast by invoking Forecast Agent"""
        logger.info(f"[{self.agent_id}] Getting forecast via Forecast Agent")

        if 'error' in state:
            return state

        org_id = state['org_id']

        try:
            # Use Forecast Agent to produce forecast output
            forecast_output = await run_forecasting_agent(org_id)

            # Forecast agent returns output containing 'forecast' (see Forecast_Agent/agent.py)
            # fall back to 'forecast_results' used internally if needed
            forecast_data = forecast_output.get('forecast') or forecast_output.get('forecast_results') or []

            state['forecast'] = forecast_data
            state['forecast_meta'] = {
                'model_info': forecast_output.get('model_info') or forecast_output.get('model_info', {})
            }
            state['current_step'] = 'forecast_retrieved'

            logger.info(f"Forecast retrieved: {len(forecast_data)} days from Forecast Agent")

        except Exception as e:
            logger.error(f"Error getting forecast: {e}")
            state['error'] = str(e)

        return state
    
    async def get_mandatory_expenses(self, state: Dict) -> Dict:
        """Fetch mandatory expenses (payroll, rent, loan, GST, tax)"""
        logger.info(f"[{self.agent_id}] Fetching mandatory expenses")
        
        if 'error' in state:
            return state
        
        org_id = state['org_id']
        
        try:
            today = datetime.now().date()
            end_date = today + timedelta(days=91)
            
            bills_response = await self.client.get(
                f"/bills/org/{org_id}/summary",
                params={
                    "from": today.strftime('%Y-%m-%d'),
                    "to": end_date.strftime('%Y-%m-%d')
                }
            )
            bills_data = bills_response.json()
            
            bills_list = await self.client.get(
                f"/bills/org/{org_id}",
                params={
                    "from": today.strftime('%Y-%m-%d'),
                    "to": end_date.strftime('%Y-%m-%d')
                }
            )
            bills_detail = bills_list.json()
            
            # Extract mandatory expenses
            mandatory_expenses = {}
            mandatory_categories = ['payroll', 'salary', 'rent', 'loan', 'emf', 'gst', 'tax', 'statutory']
            
            for bill in bills_detail.get('bills', []):
                category = (bill.get('expense_category', '') or bill.get('category', '')).lower()
                due_date_raw = bill.get('due_date')
                due_parsed = self._parse_date(due_date_raw)
                if due_parsed:
                    due_key = due_parsed.strftime('%Y-%m-%d')
                else:
                    continue  # skip bills without a valid due date

                amount = self._to_float(bill.get('amount', 0))

                is_mandatory = any(cat in category for cat in mandatory_categories)

                if is_mandatory:
                    if due_key not in mandatory_expenses:
                        mandatory_expenses[due_key] = {
                            'total': 0.0,
                            'items': [],
                            'categories': []
                        }
                    mandatory_expenses[due_key]['total'] += amount
                    mandatory_expenses[due_key]['items'].append({
                        'bill_id': bill.get('bill_id'),
                        'category': category,
                        'amount': amount,
                        'due_date': due_key
                    })
                    if category not in mandatory_expenses[due_key]['categories']:
                        mandatory_expenses[due_key]['categories'].append(category)
            
            state['mandatory_expenses'] = mandatory_expenses
            state['total_mandatory_91d'] = sum(self._to_float(exp['total'], 0.0) for exp in mandatory_expenses.values())
            state['current_step'] = 'mandatory_expenses_retrieved'
            
            logger.info(f"Mandatory expenses: ₹{state['total_mandatory_91d']:,.0f}")
            
        except Exception as e:
            logger.error(f"Error fetching mandatory expenses: {e}")
            state['mandatory_expenses'] = {}
        
        return state
    
    async def get_credit_limits(self, state: Dict) -> Dict:
        """Get credit limits and available credit"""
        logger.info(f"[{self.agent_id}] Fetching credit limits")
        
        if 'error' in state:
            return state
        
        org_id = state['org_id']
        
        try:
            # GET /organizations/{orgId}/summary includes credit info
            org_response = await self.client.get(f"/organizations/{org_id}/summary")
            org_data = org_response.json()
            
            credit_line_limit = org_data.get('credit_line_limit', 0)
            credit_line_utilized = org_data.get('credit_line_utilized', 0)
            available_credit = credit_line_limit - credit_line_utilized
            
            state['credit_line_limit'] = float(credit_line_limit)
            state['credit_line_utilized'] = float(credit_line_utilized)
            state['available_credit'] = float(available_credit)
            state['credit_utilization_pct'] = (credit_line_utilized / credit_line_limit * 100) if credit_line_limit > 0 else 0
            state['current_step'] = 'credit_limits_retrieved'
            
            logger.info(f"Available credit: ₹{available_credit:,.0f}")
            
        except Exception as e:
            logger.error(f"Error fetching credit limits: {e}")
            state['credit_line_limit'] = 0
            state['available_credit'] = 0
        
        return state
    
    async def detect_collisions(self, state: Dict) -> Dict:
        """Detect collision dates"""
        logger.info(f"[{self.agent_id}] Detecting collisions")
        
        if 'error' in state:
            return state
        
        forecast = state.get('forecast', [])
        mandatory = state.get('mandatory_expenses', {})
        minimum_balance = state.get('minimum_balance', 0)
        available_credit = state.get('available_credit', 0)
        
        collisions = []
        
        for forecast_item in forecast:
            fdate_raw = forecast_item.get('date')
            fdate_parsed = self._parse_date(fdate_raw)
            fkey = fdate_parsed.strftime('%Y-%m-%d') if fdate_parsed else str(fdate_raw)[:10]
            balance = self._to_float(forecast_item.get('predicted_balance', 0))
            mandatory_for_date = self._to_float(mandatory.get(fkey, {}).get('total', 0))
            balance_after_mandatory = balance - mandatory_for_date
            
            # Check if collision occurs
            if balance_after_mandatory < minimum_balance:
                deficit = minimum_balance - balance_after_mandatory
                
                # Can credit line cover it?
                credit_can_cover = deficit <= available_credit
                
                _parsed = self._parse_date(fkey)
                days_from_now = (_parsed - datetime.now().date()).days if _parsed else 0

                collision = {
                    'collision_date': fkey,
                    'predicted_balance': float(balance),
                    'mandatory_expenses': mandatory_for_date,
                    'balance_after_mandatory': balance_after_mandatory,
                    'deficit_amount': abs(deficit),
                    'credit_can_cover': credit_can_cover,
                    'days_from_now': days_from_now,
                    'expense_categories': list(mandatory.get(fkey, {}).get('categories', set())),
                    'bills': mandatory.get(fkey, {}).get('items', [])
                }
                
                collisions.append(collision)
        
        state['collisions'] = collisions
        state['collision_count'] = len(collisions)
        state['first_collision'] = collisions[0] if collisions else None
        state['current_step'] = 'collisions_detected'
        
        logger.info(f"Collisions detected: {len(collisions)}")
        
        return state
    
    async def analyze_severity(self, state: Dict) -> Dict:
        """Analyze severity of each collision"""
        logger.info(f"[{self.agent_id}] Analyzing severity")
        
        if 'error' in state:
            return state
        
        collisions = state.get('collisions', [])
        available_credit = state.get('available_credit', 0)
        
        for collision in collisions:
            deficit = collision['deficit_amount']
            days_away = collision['days_from_now']
            
            # Severity scoring (0-100)
            # Factors: proximity, magnitude, credit coverage
            
            proximity_score = max(0, 100 - (days_away * 2))  # Closer = higher
            magnitude_score = min(100, (deficit / 1000000000 * 100))  # Larger = higher
            credit_score = 0 if collision['credit_can_cover'] else 50  # Worse if credit can't cover
            
            severity_score = (proximity_score * 0.4) + (magnitude_score * 0.35) + (credit_score * 0.25)
            
            if severity_score >= 80:
                severity = 'critical'
            elif severity_score >= 60:
                severity = 'high'
            elif severity_score >= 40:
                severity = 'medium'
            else:
                severity = 'low'
            
            collision['severity_score'] = round(severity_score, 2)
            collision['severity'] = severity
            collision['days_to_resolve'] = max(1, days_away - 2)  # Days before collision to act
        
        # Sort by severity
        collisions.sort(key=lambda x: x['severity_score'], reverse=True)
        
        state['collisions'] = collisions
        state['current_step'] = 'severity_analyzed'
        
        return state
    
    async def generate_mitigation(self, state: Dict) -> Dict:
        """Generate mitigation strategies for each collision"""
        logger.info(f"[{self.agent_id}] Generating mitigation strategies")
        
        if 'error' in state:
            return state
        
        org_id = state['org_id']
        collisions = state.get('collisions', [])
        
        try:
            customers_resp = await self.client.get(f"/customers/org/{org_id}")
            try:
                customers_json = customers_resp.json()
                if isinstance(customers_json, dict):
                    customer_data = customers_json.get('customers') or customers_json.get('data') or []
                elif isinstance(customers_json, list):
                    customer_data = customers_json
                else:
                    customer_data = []
            except Exception:
                customer_data = []
            
            today = datetime.now().date()
            invoices_resp = await self.client.get(
                f"/invoices/org/{org_id}",
                params={"from": (today - timedelta(days=90)).strftime('%Y-%m-%d')}
            )
            try:
                invoices_json = invoices_resp.json()
                if isinstance(invoices_json, dict):
                    invoice_data = invoices_json.get('invoices') or invoices_json.get('data') or []
                elif isinstance(invoices_json, list):
                    invoice_data = invoices_json
                else:
                    invoice_data = []
            except Exception:
                invoice_data = []
            
        except Exception as e:
            logger.error(f"Error fetching customer data: {e}")
            customer_data = []
            invoice_data = []
        
        # Generate mitigation for each collision
        for collision in collisions:
            mitigation_levers = []
            deficit = self._to_float(collision.get('deficit_amount', 0))
            collision_date = collision.get('collision_date')
            
            # Lever 1: Accelerate Collections
            accelerate_potential = 0.0
            top_customers_for_collection = []
            
            for invoice in invoice_data:
                status = (invoice.get('payment_status') or invoice.get('status') or '').lower()
                if status in ['open', 'partial', 'unpaid']:
                    remaining = self._to_float(invoice.get('remaining_amount') or invoice.get('outstanding') or invoice.get('amount_due') or 0)
                    customer_id = invoice.get('customer_id') or invoice.get('customerId') or invoice.get('customer')
                    customer_name = invoice.get('customer_name') or invoice.get('customerName') or invoice.get('customer_name')
                    due_date = invoice.get('due_date') or invoice.get('dueDate')
                    
                    due_parsed = self._parse_date(due_date)
                    coll_parsed = self._parse_date(collision_date)
                    if due_parsed and coll_parsed and due_parsed < coll_parsed:
                        accelerate_potential += remaining

                        customer = next((c for c in customer_data if (str(c.get('customer_id')) == str(customer_id)) or (str(c.get('id')) == str(customer_id))), {})
                        reliability = self._to_float(customer.get('payment_reliability_score', customer.get('reliability', 0.5)), 0.5)
                        
                        top_customers_for_collection.append({
                            'customer_id': customer_id,
                            'amount': remaining,
                            'due_date': due_date,
                            'reliability_score': reliability,
                            'collection_probability': reliability * 0.9
                        })
            
            top_customers_for_collection.sort(
                key=lambda x: x['amount'] * x.get('collection_probability', 0),
                reverse=True
            )
            
            if accelerate_potential > 0:
                mitigation_levers.append({
                    'lever': 'accelerate_collections',
                    'priority': 1,
                    'potential_amount': float(accelerate_potential),
                    'implementation_time_days': 1,
                    'success_probability': 0.75,
                    'description': f'Accelerate collections from {len(top_customers_for_collection)} overdue customers',
                    'target_customers': top_customers_for_collection[:5],
                    'actions': [
                        'Contact top customers for immediate payment',
                        'Offer 2% early payment discount if paid within 48 hours',
                        'Escalate to senior management for key customers'
                    ]
                })
            
            # Lever 2: Defer Payables
            defer_potential = 0.0
            deferrable_bills = []
            
            for bill in collision.get('bills', []):
                category = (bill.get('category') or bill.get('expense_category') or '').lower()
                amount = self._to_float(bill.get('amount', 0))
                if category not in ['payroll', 'salary', 'statutory', 'tax', 'gst']:
                    defer_potential += amount
                    deferrable_bills.append(bill)
            
            if defer_potential > 0:
                mitigation_levers.append({
                    'lever': 'defer_payables',
                    'priority': 2,
                    'potential_amount': float(defer_potential),
                    'implementation_time_days': 1,
                    'success_probability': 0.6,
                    'description': f'Defer {len(deferrable_bills)} non-critical vendor payments',
                    'target_bills': deferrable_bills,
                    'actions': [
                        'Contact vendors for 30-day payment extension',
                        'Emphasize long-term partnership and previous good payment history',
                        'Offer to prioritize payment in next cycle'
                    ]
                })
            
            # Lever 3: Draw Credit Line
            available_credit = self._to_float(state.get('available_credit', 0))
            
            if available_credit > deficit * 0.5:
                mitigation_levers.append({
                    'lever': 'draw_credit_line',
                    'priority': 3,
                    'potential_amount': float(available_credit),
                    'implementation_time_days': 0,
                    'success_probability': 0.95,
                    'description': f'Draw ₹{available_credit:,.0f} from available credit line',
                    'credit_amount': float(available_credit),
                    'interest_cost_1day': available_credit * 0.0008,
                    'actions': [
                        'Initiate credit line draw with bank',
                        'Prepare required documentation',
                        'Confirm funds transfer'
                    ]
                })
            
            # Lever 4: Restructure Loan EMI
            loan_emi_deferrable = 0.0
            if 'loan' in ' '.join([str(x).lower() for x in collision.get('expense_categories', [])]):
                loan_emi_deferrable = self._to_float(collision.get('mandatory_expenses', 0)) * 0.3
                
                if loan_emi_deferrable > 0:
                    mitigation_levers.append({
                        'lever': 'restructure_loan',
                        'priority': 4,
                        'potential_amount': float(loan_emi_deferrable),
                        'implementation_time_days': 3,
                        'success_probability': 0.5,
                        'description': 'Negotiate loan restructuring with lender',
                        'monthly_savings': float(loan_emi_deferrable),
                        'additional_cost': loan_emi_deferrable * 0.05,
                        'actions': [
                            'Schedule call with loan officer',
                            'Present financial situation and recovery plan',
                            'Negotiate 2-3 month EMI moratorium',
                            'Document agreement'
                        ]
                    })
            
            total_potential = sum(self._to_float(lever.get('potential_amount', 0)) * self._to_float(lever.get('success_probability', 0))
                                  for lever in mitigation_levers)
            
            collision['mitigation_levers'] = mitigation_levers
            collision['total_mitigation_potential'] = float(total_potential)
            collision['can_be_mitigated'] = total_potential >= deficit * 0.7
        
        # Ensure numeric fields at top-level collisions
        for c in collisions:
            c['deficit_amount'] = self._to_float(c.get('deficit_amount', 0))
            c['balance_after_mandatory'] = self._to_float(c.get('balance_after_mandatory', 0))
        
        state['collisions'] = collisions
        state['current_step'] = 'mitigation_generated'
        
        logger.info(f"Mitigation strategies generated for {len(collisions)} collisions")
        
        return state
    
    async def prepare_output(self, state: Dict) -> Dict:
        """Prepare final output"""
        logger.info(f"[{self.agent_id}] Preparing output")
        
        if 'error' in state:
            state['output'] = {'status': 'error', 'message': state['error']}
            return state
        
        collisions = state.get('collisions', [])
        
        # Emergency action plan for first collision (if any)
        emergency_plan = None
        if collisions and len(collisions) > 0:
            first_collision = collisions[0]
            if first_collision.get('severity') in ['critical', 'high']:
                # compute expected recovery from mitigation levers (safe)
                expected_recovery = 0
                for lever in first_collision.get('mitigation_levers', []):
                    for tc in lever.get('target_customers', []):
                        expected_recovery += tc.get('amount', 0)
                expected_deferral = sum(
                    lever.get('potential_amount', 0)
                    for lever in first_collision.get('mitigation_levers', [])
                    if lever.get('lever') == 'defer_payables'
                )
                emergency_plan = {
                    'action_date': (self._parse_date(first_collision['collision_date']) - timedelta(days=2)).strftime('%Y-%m-%d') if self._parse_date(first_collision['collision_date']) else None,
                    'priority_actions': [
                        {
                            'action_id': 1,
                            'action': 'URGENT: Contact top 5 customers for immediate payment',
                            'owner': 'Sales Manager',
                            'deadline': (self._parse_date(first_collision['collision_date']) - timedelta(days=1)).strftime('%Y-%m-%d') if self._parse_date(first_collision['collision_date']) else None,
                            'expected_recovery': expected_recovery
                        },
                        {
                            'action_id': 2,
                            'action': 'Draw available credit line if needed',
                            'owner': 'Finance Manager',
                            'deadline': first_collision['collision_date'],
                            'amount': state.get('available_credit', 0)
                        },
                        {
                            'action_id': 3,
                            'action': 'Contact non-critical vendors for payment deferral',
                            'owner': 'Procurement Manager',
                            'deadline': (self._parse_date(first_collision['collision_date']) - timedelta(days=1)).strftime('%Y-%m-%d') if self._parse_date(first_collision['collision_date']) else None,
                            'expected_deferral': expected_deferral
                        }
                    ]
                }
        
        state['output'] = {
            'status': 'success',
            'agent_id': self.agent_id,
            'org_id': state['org_id'],
            'timestamp': datetime.now().isoformat(),
            'current_position': {
                'current_balance': state.get('current_balance', 0),
                'minimum_balance': state.get('minimum_balance', 0),
                'balance_gap': state.get('balance_gap', 0),
                'available_credit': state.get('available_credit', 0),
                'credit_utilization_pct': state.get('credit_utilization_pct', 0)
            },
            'collision_analysis': {
                'total_collisions_detected': state.get('collision_count', 0),
                'critical_collisions': len([c for c in collisions if c['severity'] == 'critical']),
                'high_collisions': len([c for c in collisions if c['severity'] == 'high']),
                'first_collision': state.get('first_collision'),
                'collisions_91d': collisions
            },
            'mandatory_expenses_91d': {
                'total_amount': state.get('total_mandatory_91d', 0),
                'expense_dates': sorted(state.get('mandatory_expenses', {}).keys())
            },
            'emergency_action_plan': emergency_plan,
            'recommendation': {
                'immediate_action': 'URGENT' if state.get('collision_count', 0) > 0 else 'MONITOR',
                'message': f"⚠️ {state.get('collision_count', 0)} collision(s) detected in next 91 days" if state.get('collision_count', 0) > 0 else "✅ No collisions detected in 91-day forecast"
            }
        }
        
        state['current_step'] = 'complete'
        
        return state

