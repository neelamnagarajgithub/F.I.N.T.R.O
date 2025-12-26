from agent import runway_agent
from datetime import date

result = runway_agent.invoke({
    "org_id": 1,
    "period_start": None,   # or last 90 days
    "period_end": None,
    "opening_balance": 10_000_000  # ₹1 Cr
})

print("\n--- RUNWAY ANALYSIS ---")
print(f"Runway Days: {result['runway_days']:.1f}")
print(f"Runway Months: {result['runway_months']:.1f}")
print(f"Risk Level: {result['risk_level']}")
print("\nExplanation:\n", result["explanation"])
