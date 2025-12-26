def aggregate_insights(agent_outputs):
    return {
        "cash_health": agent_outputs["agent1"],
        "forecast": agent_outputs["agent2"],
        "risk": agent_outputs["agent3"],
        "collisions": agent_outputs["agent4"],
        "collections": agent_outputs["agent5"],
        "scenarios": agent_outputs["agent6"]
    }
