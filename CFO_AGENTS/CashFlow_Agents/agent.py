from langgraph.graph import StateGraph, END
from .state import CashflowState
from .fetchers import fetch_payments
from .compute import compute_cashflow
from .explain import explain_cashflow

def fetch_node(state: CashflowState):
    payments = fetch_payments(
        state["org_id"],
        state.get("period_start"),
        state.get("period_end")
    )
    state["payments"] = payments
    return state

def compute_node(state: CashflowState):
    return compute_cashflow(state, state["payments"])

def explain_node(state: CashflowState):
    return explain_cashflow(state)

graph = StateGraph(CashflowState)

graph.add_node("fetch", fetch_node)
graph.add_node("compute", compute_node)
graph.add_node("explain", explain_node)

graph.set_entry_point("fetch")
graph.add_edge("fetch", "compute")
graph.add_edge("compute", "explain")
graph.add_edge("explain", END)

cashflow_agent = graph.compile()
