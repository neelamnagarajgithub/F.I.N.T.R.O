def identify_risks_and_opportunities(data):
    risks = []
    opportunities = []

    for r in data["risk"]["high_risk_customers"][:3]:
        risks.append({
            "type": "Customer Risk",
            "detail": f"{r['customer']} default risk",
            "severity": r["risk_level"],
            "mitigation": "Accelerate collections / renegotiate terms"
        })

    for o in data["collections"]["top_quick_wins"][:3]:
        opportunities.append({
            "type": "Collections",
            "detail": f"₹{o['amount']} from {o['customer']}",
            "action": "Immediate follow-up",
            "impact": "Improves cash runway"
        })

    return risks, opportunities
