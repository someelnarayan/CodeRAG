# llm/llm.py

import os
import requests
import time

from groq import Groq

from setting.settings import OLLAMA_BASE_URL, LLM_MODEL, USE_GROQ, USE_OLLAMA


GROQ_TIMEOUT = 4
OLLAMA_TIMEOUT = 10


groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ==============================
# GROQ PRIMARY
# ==============================

def generate_answer_groq(question, context_chunks):

    context = "\n\n".join(context_chunks)

    prompt = f"""
You are a senior software engineer.

Use the code context to answer the question.

Code Context:
{context}

Question:
{question}

Answer clearly:
"""

    try:

        t0 = time.time()

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=512
        )

        elapsed = time.time() - t0

        answer = response.choices[0].message.content

        print(f"Groq success in {elapsed:.2f}s")

        return answer, True

    except Exception as e:

        print(f"Groq error: {e}")

        return None, False


# ==============================
# OLLAMA FALLBACK
# ==============================

def generate_answer_local(question, context_chunks):

    context = "\n\n".join(context_chunks)

    prompt = f"""
You are a senior software engineer.

Use the code context to answer the question.

Code Context:
{context}

Question:
{question}

Answer clearly:
"""

    try:

        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=OLLAMA_TIMEOUT
        )

        r.raise_for_status()

        data = r.json()

        return data.get("response", ""), True

    except Exception as e:

        print(f"Ollama error: {e}")

        return None, False


# ==============================
# MAIN GENERATION LOGIC
# ==============================

def generate_answer(question, context_chunks):

    print("\nTrying Groq (primary)...")

    # Try Groq first
    answer, success = generate_answer_groq(question, context_chunks)

    if success:
        return answer

    # If Groq failed AND Ollama allowed
    if USE_OLLAMA:

        print("Groq failed or slow → falling back to Ollama")

        answer, success = generate_answer_local(question, context_chunks)

        if success:
            return answer

    # If both fail
    return (
        "Sorry, I couldn't generate an answer right now. "
        "Both Groq and Ollama failed."
    )