from typing import TypedDict, Optional, List, Any
from datetime import date

class CashflowState(TypedDict):
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
