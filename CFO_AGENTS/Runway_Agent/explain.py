from config import llm

def explain_runway(state):
    prompt = f"""
You are a CFO AI.

Explain the company’s cash runway situation clearly to a founder.

Facts:
- Opening balance: ₹{state['opening_balance']:,.2f}
- Average daily burn: ₹{state['avg_daily_burn']:,.2f}
- Monthly burn: ₹{state['monthly_burn']:,.2f}
- Runway: {state['runway_days']:.1f} days (~{state['runway_months']:.1f} months)
- Risk level: {state['risk_level']}

Explain:
1. What this runway means
2. How urgent the situation is
3. One concrete action recommendation
"""

    response = llm.invoke(prompt)
    state["explanation"] = response.content
    return state
