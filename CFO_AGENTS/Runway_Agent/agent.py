from langgraph.graph import StateGraph, END
from state import RunwayState
from fetchers import fetch_payments
from compute import compute_runway
from explain import explain_runway

def fetch_node(state: RunwayState):
    payments = fetch_payments(
        state["org_id"],
        state.get("period_start"),
        state.get("period_end")
    )
    state["payments"] = payments
    return state

def compute_node(state: RunwayState):
    return compute_runway(state, state["payments"])

def explain_node(state: RunwayState):
    return explain_runway(state)

graph = StateGraph(RunwayState)

graph.add_node("fetch", fetch_node)
graph.add_node("compute", compute_node)
graph.add_node("explain", explain_node)

graph.set_entry_point("fetch")
graph.add_edge("fetch", "compute")
graph.add_edge("compute", "explain")
graph.add_edge("explain", END)

runway_agent = graph.compile()
