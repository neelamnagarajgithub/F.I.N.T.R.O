from collections_agent.agent import collections_agent

result = collections_agent.invoke({
    "org_id": 1,
    "overdue_receivables": overdue_from_agent_3,
    "customer_risk_scores": risk_scores_from_agent_3,
    "payment_history": history_map,
    "collisions": collisions_from_agent_4
})

print("\nTOP 10 TO CALL TODAY:")
for i in result["prioritized_queue"][:10]:
    print(i)

print("\nRECOVERY METRICS:")
print(result["metrics"])
