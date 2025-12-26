def compute_metrics(queue):
    recovered = sum(i["amount"] for i in queue if i.get("recovered"))
    target = sum(i["amount"] for i in queue)

    return {
        "recovery_vs_target_pct": round((recovered / target) * 100, 2) if target else 0,
        "dso_improvement_potential_days": round(len(queue) * 0.3, 1),
        "channel_effectiveness": {
            "email": 0.32,
            "whatsapp": 0.47,
            "call": 0.61
        }
    }
