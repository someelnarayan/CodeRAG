# =====================
# IMPORTS
# =====================
import os
import requests
from groq import Groq
from setting.settings import OLLAMA_BASE_URL, LLM_MODEL, USE_GROQ


# =====================
# LOCAL LLaMA (OLLAMA)
# =====================
def generate_answer_local(question, context_chunks):
    context = "\n\n".join(context_chunks)

    prompt = f"""
You are a senior software engineer.
Use the code context to answer the question.

Code Context:
{context}

Question: {question}
Answer clearly:
"""

    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": LLM_MODEL, "prompt": prompt, "stream": False}
    )

    data = r.json()
    return data.get("response", "Error: No response from local model")


# =====================
# GROQ (FAST CLOUD LLM)
# =====================
groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def generate_answer_groq(question, context_chunks):
    context = "\n\n".join(context_chunks)

    prompt = f"""
You are a senior software engineer.
Use the code context to answer the question.

Code Context:
{context}

Question: {question}
Answer clearly:
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=512
        )

        return response.choices[0].message.content
    except Exception as e:
        # Surface the error so caller can mark task failed and log
        print("GROQ ERROR:", repr(e))
        raise


# =====================
# 🔁 HYBRID SWITCH (FINAL)
# =====================

def generate_answer(question, context_chunks):
    if USE_GROQ:
        return generate_answer_groq(question, context_chunks)
    else:
        return generate_answer_local(question, context_chunks)
