def generate_alerts(data):
    alerts = []

    for c in data["collisions"]["critical"]:
        alerts.append({
            "type": "Liquidity Risk",
            "message": f"Cash crunch expected on {c['date']}",
            "severity": "CRITICAL",
            "action": "Immediate intervention required"
        })

    return alerts
