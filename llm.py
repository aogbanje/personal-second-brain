from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_PROVIDER, XKIRO_API_KEY, XKIRO_BASE_URL, XKIRO_MODEL

async def query_second_brain(query: str, retrieved_contexts: list):
    if LLM_PROVIDER != "xkiro":
        return
        
    if not XKIRO_API_KEY:
        print("❌ System Error: Missing XKIRO_API_KEY.")
        return

    # Use the ChatOpenAI class but point it entirely to xKiro's interface
    llm = ChatOpenAI(
        model=XKIRO_MODEL,
        temperature=0.2,
        openai_api_key=XKIRO_API_KEY,
        base_url=XKIRO_BASE_URL # Crucial: forces LangChain to talk to xKiro
    )

    context_str = "\n\n---\n\n".join(retrieved_contexts)

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an advanced Personal Second Brain cognitive assistant.\n"
            "Answer the user's question using ONLY the provided document contexts below.\n"
            "=== RETRIEVED DOCUMENT CONTEXT ===\n"
            "{context}"
        )),
        ("human", "{question}")
    ])

    print(f"🤖 Shipping bounded query through xKiro gateway [{XKIRO_MODEL}]...")
    try:
        messages = prompt_template.format_messages(context=context_str, question=query)
        response = await llm.ainvoke(messages)
        print(f"\n🧠 [Second Brain Answer]:\n{response.content}\n")
        return response.content
    except Exception as e:
        print(f"❌ Error during model execution trace: {e}")
