from .config import llm

def explain_cashflow(state):
    if state["period_start"] and state["period_end"]:
        scope = f"between {state['period_start']} and {state['period_end']}"
    else:
        scope = "across the full available transaction history"

    prompt = f"""
You are a CFO AI.

Explain the cashflow situation {scope}.

Facts:
- Inflows: ₹{state['inflows']:,.2f}
- Outflows: ₹{state['outflows']:,.2f}
- Net cashflow: ₹{state['net_cashflow']:,.2f}
- Opening balance: ₹{state['opening_balance']:,.2f}
- Closing balance: ₹{state['closing_balance']:,.2f}
- Burn rate (monthly): ₹{state['burn_rate']:,.2f}
- Risk level: {state['risk_level']}

Give a clear, executive-level explanation and key risk insight.
"""

    response = llm.invoke(prompt)
    state["explanation"] = response.content
    return state
