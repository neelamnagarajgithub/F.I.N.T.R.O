def generate_action_checklist(data):
    actions = []

    priorities = [
        ("Collect from high-risk customer", "RED"),
        ("Delay non-critical vendor payments", "ORANGE"),
        ("Trigger credit line draw", "RED"),
        ("Renegotiate rent", "YELLOW")
    ]

    for i, (action, color) in enumerate(priorities):
        actions.append({
            "priority": i + 1,
            "action": action,
            "owner": "Finance Head",
            "deadline": "7 days",
            "impact": "Improves liquidity",
            "urgency": color
        })

    return actions[:12]
