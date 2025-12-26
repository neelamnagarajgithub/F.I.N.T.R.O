from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.3
)

def generate_executive_brief(context):
    prompt = f"""
    You are a CFO Copilot.

    Using the following data, generate a concise executive briefing:
    {context}

    Structure:
    - Key Metrics Summary
    - Top 3 Risks + Mitigations
    - Top 3 Opportunities + Actions
    - Collections Status
    - Cash Outlook (30/60/90 days)
    """

    return llm.invoke(prompt).content
