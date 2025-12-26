from typing import TypedDict, List, Dict

class CollectionsState(TypedDict):
    org_id: int

    overdue_receivables: List[Dict]
    customer_risk_scores: Dict[int, float]
    payment_history: Dict[int, List[Dict]]
    collisions: List[Dict]

    prioritized_queue: List[Dict]
    drafted_messages: List[Dict]
    metrics: Dict
