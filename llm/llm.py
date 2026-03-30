# llm/llm.py

import requests
import time
import os
from pathlib import Path
from dotenv import dotenv_values
from groq import Groq

from setting.settings import OLLAMA_BASE_URL, LLM_MODEL, USE_OLLAMA

# ==============================
# ENV LOAD
# ==============================

# ✅ FIXED: always read .env from project root
BASE_DIR = Path(__file__).resolve().parent.parent
env_config = dotenv_values(BASE_DIR / ".env")

GROQ_API_KEY = (
    os.getenv("GROQ_API_KEY")
    or env_config.get("GROQ_API_KEY")
    or ""
).strip()

print("Using GROQ KEY:", GROQ_API_KEY[:10] if GROQ_API_KEY else "None")

GROQ_TIMEOUT = 30       # ✅ FIXED: was 4 — too low, caused timeouts
OLLAMA_TIMEOUT = 10

# ==============================
# GROQ INIT
# ==============================

groq_client = None

if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("Groq client initialized successfully")
    except Exception as e:
        print("Groq initialization failed:", str(e))
else:
    print("GROQ_API_KEY not found")

# ==============================
# GROQ PRIMARY
# ==============================

def generate_answer_groq(question, context_chunks):

    if not groq_client:
        print("Groq client not available")
        return None, False

    if not context_chunks:
        print("No context provided")
        return None, False

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
        start_time = time.time()

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=512,
            timeout=GROQ_TIMEOUT
        )

        duration = time.time() - start_time

        answer = response.choices[0].message.content

        print(f"Groq response received in {duration:.2f}s")

        return answer, True

    except Exception as e:
        print("Groq API error:", type(e).__name__, str(e))
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
        start_time = time.time()

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=OLLAMA_TIMEOUT
        )

        response.raise_for_status()
        data = response.json()

        duration = time.time() - start_time

        print(f"Ollama response received in {duration:.2f}s")

        return data.get("response", ""), True

    except requests.exceptions.ConnectionError:
        print("Ollama connection failed:", OLLAMA_BASE_URL)
        return None, False
    except requests.exceptions.Timeout:
        print("Ollama request timeout")
        return None, False
    except Exception as e:
        print("Ollama error:", str(e))
        return None, False


# ==============================
# MAIN GENERATION LOGIC
# ==============================

def generate_answer(question, context_chunks):

    print("Trying Groq...")

    answer, success = generate_answer_groq(question, context_chunks)

    if success:
        return answer

    print("Groq failed. Trying fallback...")

    if USE_OLLAMA:
        answer, success = generate_answer_local(question, context_chunks)
        if success:
            return answer

    return (
        "Sorry, unable to generate answer right now. "
        "Groq failed and fallback is not available."
    )
