from agent import cashflow_agent
from datetime import date

result = cashflow_agent.invoke({
    "org_id": 2,
    "period_start": date(2025, 9, 1),
    "period_end":date(2025, 11, 2)
})

print("\n--- CASHFLOW SUMMARY ---")
print("Risk:", result["risk_level"])
print("Closing Balance:", result["closing_balance"])
print("\nExplanation:\n", result["explanation"])
print("Inflows: ₹{:,}".format(result["inflows"]))
print("Outflows: ₹{:,}".format(result["outflows"]))
print("Net Cashflow: ₹{:,}".format(result["net_cashflow"]))
print("Opening Balance: ₹{:,}".format(result["opening_balance"]))
print("Closing Balance: ₹{:,}".format(result["closing_balance"]))
print("Burn Rate (monthly): ₹{:,}".format(int(result["burn_rate"])))
print("------------------------\n")