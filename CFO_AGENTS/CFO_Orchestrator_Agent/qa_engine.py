def answer_cfo_question(question, context):
    prompt = f"""
    You are an AI CFO Advisor.

    CFO Question:
    "{question}"

    Available Data:
    {context}

    Rules:
    - Answer using data only
    - Show reasoning
    - Cite data source
    - Give confidence score (0–1)
    """

    response = llm.invoke(prompt).content

    return {
        "answer": response,
        "confidence": 0.87  # later auto-calc via retrieval coverage
    }
