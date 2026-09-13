import os
import sys
import asyncio
from openai import AsyncOpenAI
from config import LLM_PROVIDER, XKIRO_API_KEY, XKIRO_BASE_URL, XKIRO_MODEL

async def query_second_brain(query: str, retrieved_contexts: list):
    """
    Directly routes prompts and context facts through the native AsyncOpenAI client.
    """
    # Diagnostic log to verify configuration values inside the execution block
    print(f"🔍 Executing LLM block | Active Provider Config: '{LLM_PROVIDER}' | Target Model: '{XKIRO_MODEL}'")

    if not XKIRO_API_KEY or "your_" in XKIRO_API_KEY:
        print("❌ Configuration Error: Missing a valid XKIRO_API_KEY in your .env file.", file=sys.stderr)
        return None

    # Handle Chroma DB data structure variance safely
    # If Chroma returns a list of lists (e.g. [['text1', 'text2']]), flatten it down
    if retrieved_contexts and isinstance(retrieved_contexts[0], list):
        flattened_contexts = retrieved_contexts[0]
    else:
        flattened_contexts = retrieved_contexts

    # Convert the array of text fragments into a formatted string block
    context_str = "\n\n---\n\n".join(flattened_contexts)
    clean_base_url = XKIRO_BASE_URL.strip().rstrip('/')

    print(f"🤖 Connecting to xKiro network channel via {clean_base_url}...")
    
    try:
        # Initialize the native async connection engine
        client = AsyncOpenAI(
            api_key=XKIRO_API_KEY,
            base_url=clean_base_url
        )

        # Invoke the chat completions request payload
        response = await client.chat.completions.create(
            model=XKIRO_MODEL.strip(),
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are an advanced Personal Second Brain cognitive assistant.\n"
                        "Answer the user's question using ONLY the provided document contexts below.\n"
                        "If the answer cannot be confidently derived from the context, state clearly that you do not know.\n\n"
                        f"=== RETRIEVED DOCUMENT CONTEXT ===\n{context_str}"
                    )
                },
                {"role": "user", "content": query}
            ],
            temperature=0.2
        )
        
        answer = response.choices[0].message.content
        print(f"\n🧠 [Second Brain Answer]:\n{answer}\n")
        return answer

    except Exception as e:
        print(f"❌ Network channel error during xKiro API call trace: {e}", file=sys.stderr)
        return None
