def recommend_intervention(item):
    if item["days_overdue"] > 90:
        return "legal_escalation"
    if item["risk_score"] > 75:
        return "upfront_payment_or_block"
    if item["days_overdue"] > 45:
        return "structured_payment_plan"
    if item["days_overdue"] > 20:
        return "early_payment_discount"
    return "soft_reminder"
