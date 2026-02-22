import os
import requests
import time
from groq import Groq
from setting.settings import OLLAMA_BASE_URL, LLM_MODEL, USE_GROQ

# Ollama runs locally - if it takes > 2 seconds, we'll fall back to Groq
OLLAMA_TIMEOUT = 2.0


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
    Try Ollama first. If it times out or errors, use Groq.
    If both fail, return a helpful error message.
    """
    
    # Try local Ollama first (if not disabled)
    if not USE_GROQ:
        print("\nTrying Ollama (local)...")
        answer, success, elapsed = generate_answer_local(question, context_chunks)
        
        if success:
            print(f"  Got answer in {elapsed:.2f}s")
            return answer
        elif elapsed < OLLAMA_TIMEOUT:
            # Error, not timeout
            print("  Ollama failed, falling back to Groq")
        else:
            # Timeout
            print(f"  Ollama too slow ({elapsed:.2f}s), trying Groq instead")
    
    # Fallback to Groq
    print("Trying Groq (cloud)...")
    answer, success = generate_answer_groq(question, context_chunks)
    
    if success:
        return answer
    
    # Both failed
    return (
        "Sorry, I couldn't generate an answer right now. "
        "Both local Ollama and cloud Groq failed. "
        "Try again in a moment or check your configuration."
    )
