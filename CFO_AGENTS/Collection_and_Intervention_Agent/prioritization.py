def collision_proximity_weight(collisions):
    if not collisions:
        return 1

    days = min(c["days_until"] for c in collisions)
    return max(1, 30 / max(days, 1))  # closer collision = higher weight


def prioritize_receivables(receivables, risk_scores, collisions):
    weight = collision_proximity_weight(collisions)

    ranked = []
    for r in receivables:
        score = (
            risk_scores.get(r["customer_id"], 50)
            * r["days_overdue"]
            * r["amount"]
            * weight
        )

        ranked.append({
            **r,
            "priority_score": score
        })

    ranked.sort(key=lambda x: x["priority_score"], reverse=True)
    return ranked
