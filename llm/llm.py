import os
import requests
import time
from groq import Groq
from setting.settings import (
    OLLAMA_BASE_URL,
    LLM_MODEL,
    USE_GROQ,
    ENABLE_OLLAMA,
    OLLAMA_TIMEOUT_SECONDS,
)

# Ollama runs locally - use timeout from settings
OLLAMA_TIMEOUT = float(OLLAMA_TIMEOUT_SECONDS)


def generate_answer_local(question, context_chunks, timeout=OLLAMA_TIMEOUT):
    """Call local Ollama model - fast but might timeout."""
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
        t0 = time.time()
        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
            timeout=timeout
        )
        elapsed = time.time() - t0
        
        data = r.json()
        answer = data.get("response", "No response from Ollama")
        return answer, True, elapsed
    
    except requests.exceptions.Timeout:
        elapsed = time.time() - t0
        print(f"Ollama timeout after {elapsed:.2f}s (limit: {timeout}s)")
        return None, False, elapsed
    except Exception as e:
        elapsed = time.time() - t0
        print(f"Ollama error: {e}")
        return None, False, elapsed


# Cloud LLM - slower but reliable
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_answer_groq(question, context_chunks):
    """Call Groq cloud API - slower but reliable."""
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


def generate_answer(question, context_chunks):
    """
    Prefer Groq (cloud) when `USE_GROQ` is enabled. If Groq fails and
    `ENABLE_OLLAMA` is true, attempt the local Ollama model as a fallback.
    If `USE_GROQ` is false the function will try Ollama first (if enabled)
    then Groq.
    """
    # If Groq is primary, try it first
    if USE_GROQ:
        print("Trying Groq (cloud)...")
        answer, success = generate_answer_groq(question, context_chunks)
        if success:
            return answer

        # Groq failed — attempt local Ollama if allowed
        if ENABLE_OLLAMA:
            print("Groq failed — attempting local Ollama as fallback...")
            answer, success, elapsed = generate_answer_local(question, context_chunks)
            if success:
                print(f"  Ollama answered in {elapsed:.2f}s")
                return answer
            else:
                print("  Ollama fallback failed")

        return (
            "Sorry, I couldn't generate an answer right now. "
            "Primary cloud LLM (Groq) failed" + (
                ", and local Ollama fallback is disabled." if not ENABLE_OLLAMA else ", and fallback also failed."
            )
        )

    # If USE_GROQ is False, prefer Ollama (if enabled)
    print("USE_GROQ is disabled — trying Ollama (local) first...")
    if ENABLE_OLLAMA:
        answer, success, elapsed = generate_answer_local(question, context_chunks)
        if success:
            print(f"  Got answer from Ollama in {elapsed:.2f}s")
            return answer
        else:
            print("  Ollama failed — falling back to Groq...")

    # Finally try Groq
    print("Trying Groq (cloud)...")
    answer, success = generate_answer_groq(question, context_chunks)
    if success:
        return answer

    return (
        "Sorry, I couldn't generate an answer right now. Both local Ollama and cloud Groq failed."
    )
