result = cfo_copilot_agent.invoke({
    "org_id": 1,
    "question": "Will we face a cash crunch in the next 45 days?",
    "agent_outputs": all_agent_outputs,
    "business_context": {
        "industry": "SaaS",
        "growth_stage": "Series A"
    }
})

print(result["executive_brief"])
print(result["qa_response"])
print(result["action_checklist"])
print(result["alerts"])
