def success_probability(history, risk_score):
    paid_on_time = sum(1 for p in history if p["status"] == "paid_on_time")
    total = len(history)

    reliability = paid_on_time / total if total else 0.3

    probability = (
        0.6 * reliability +
        0.4 * (1 - risk_score / 100)
    )

    return round(min(max(probability, 0.05), 0.95), 2)
