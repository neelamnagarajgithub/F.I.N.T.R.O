def compute_cashflow(state, payments):
    inflows = sum(
        float(p["payment_amount"])
        for p in payments
        if p["payment_type"] == "inflow"
    )

    outflows = sum(
        float(p["payment_amount"])
        for p in payments
        if p["payment_type"] == "outflow"
    )

    opening_balance = 1_11_000_000  # 11 Cr assumption (as you decided)
    net = inflows - outflows
    closing = opening_balance + net

    burn_rate = outflows / 30 if outflows else 0

    if closing < burn_rate * 30:
        risk = "HIGH"
    elif closing < burn_rate * 60:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    state.update({
        "inflows": inflows,
        "outflows": outflows,
        "net_cashflow": net,
        "opening_balance": opening_balance,
        "closing_balance": closing,
        "burn_rate": burn_rate,
        "risk_level": risk
    })

    return state
