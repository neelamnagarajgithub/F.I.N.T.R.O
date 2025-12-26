from typing import TypedDict, Dict, List

class CFOState(TypedDict):
    org_id: int
    question: str | None

    agent_outputs: Dict   # all agents 1–6 output
    business_context: Dict

    executive_brief: Dict
    qa_response: Dict
    action_checklist: List[Dict]
    alerts: List[Dict]
