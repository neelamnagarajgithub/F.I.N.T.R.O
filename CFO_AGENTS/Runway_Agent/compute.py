def compute_runway(state, payments):
    # Only outflows matter for runway
    outflows = [
        float(p["payment_amount"])
        for p in payments
        if p["payment_type"] == "outflow"
    ]

    days = max(len(set(p["payment_date"] for p in payments)), 1)

    total_outflow = sum(outflows)
    avg_daily_burn = total_outflow / days
    monthly_burn = avg_daily_burn * 30

    opening_balance = state["opening_balance"]

    runway_days = (
        opening_balance / avg_daily_burn
        if avg_daily_burn > 0 else float("inf")
    )

    runway_months = runway_days / 30

    # Risk classification
    if runway_months < 3:
        risk = "CRITICAL"
    elif runway_months < 6:
        risk = "HIGH"
    elif runway_months < 12:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    state.update({
        "avg_daily_burn": avg_daily_burn,
        "monthly_burn": monthly_burn,
        "runway_days": runway_days,
        "runway_months": runway_months,
        "risk_level": risk
    })

    return state
