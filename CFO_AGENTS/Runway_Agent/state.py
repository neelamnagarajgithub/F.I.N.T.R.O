from typing import TypedDict, Optional, List, Any
from datetime import date

class RunwayState(TypedDict):
    org_id: int
    period_start: Optional[date]
    period_end: Optional[date]
    
    payments: List[Any]

    opening_balance: float
    avg_daily_burn: float
    monthly_burn: float

    runway_days: float
    runway_months: float
    risk_level: str

    explanation: str
