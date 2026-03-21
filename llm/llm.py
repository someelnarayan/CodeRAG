# llm/llm.py

import os
import requests
import time
from dotenv import load_dotenv

from groq import Groq

from setting.settings import OLLAMA_BASE_URL, LLM_MODEL, USE_GROQ, USE_OLLAMA

# Ensure .env is loaded before reading environment variables
load_dotenv()

GROQ_TIMEOUT = 4
OLLAMA_TIMEOUT = 10


# Initialize Groq client with validation
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

if not GROQ_API_KEY:
    print("⚠️  WARNING: GROQ_API_KEY not found in environment variables!")
    print("   Set GROQ_API_KEY=your_key in .env to use Groq service.")
    groq_client = None
else:
    # Validate API key format
    if not GROQ_API_KEY.startswith("gsk_"):
        print(f"⚠️  WARNING: GROQ_API_KEY doesn't start with 'gsk_'")
        print(f"   Key received: {GROQ_API_KEY[:20]}...")
    
    try:
        print(f"🔄 Initializing Groq client...")
        print(f"   API Key (hidden): {GROQ_API_KEY[:20]}***{GROQ_API_KEY[-5:]}")
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("✅ Groq client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Groq client: {e}")
        groq_client = None


# ==============================
# GROQ PRIMARY
# ==============================

def generate_answer_groq(question, context_chunks):

    if not groq_client:
        print("❌ Groq client not available (API key missing)")
        return None, False

    if not context_chunks:
        print("❌ No context chunks provided")
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

        t0 = time.time()

        print(f"   📤 Sending request to Groq API...")
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=512,
            timeout=GROQ_TIMEOUT
        )

        elapsed = time.time() - t0

        answer = response.choices[0].message.content

        print(f"✅ Groq success in {elapsed:.2f}s")

        return answer, True

    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_str = str(e)
        
        # Check for common errors
        if "401" in error_str or "invalid_api_key" in error_str.lower():
            print(f"❌ Groq error (INVALID API KEY): {error_type}")
            print(f"   Your GROQ_API_KEY appears to be invalid or expired.")
            print(f"   Get a new key from: https://console.groq.com")
        elif "429" in error_str or "rate" in error_str.lower():
            print(f"❌ Groq error (RATE LIMITED): {error_type}")
            print(f"   Too many requests. Wait a moment and try again.")
        elif "timeout" in error_str.lower():
            print(f"❌ Groq error (TIMEOUT): Took too long ({GROQ_TIMEOUT}s)")
        else:
            print(f"❌ Groq error ({error_type}): {error_str}")
        
        traceback.print_exc()

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

        t0 = time.time()

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

        elapsed = time.time() - t0

        print(f"✅ Ollama success in {elapsed:.2f}s")

        return data.get("response", ""), True

    except requests.exceptions.ConnectionError:
        print(f"❌ Ollama error: Cannot connect to {OLLAMA_BASE_URL}")
        print("   Is Ollama running? Start with: docker-compose up -d")
        return None, False
    except requests.exceptions.Timeout:
        print(f"❌ Ollama error: Request timeout after {OLLAMA_TIMEOUT}s")
        return None, False
    except Exception as e:
        print(f"❌ Ollama error: {e}")
        return None, False


# ==============================
# MAIN GENERATION LOGIC
# ==============================

def generate_answer(question, context_chunks):

    print("\n🔵 Attempting Groq (primary)...")

    # Try Groq first (primary)
    answer, success = generate_answer_groq(question, context_chunks)

    if success:
        return answer

    print("\nGroq failed. Checking fallback options...")

    # If Groq failed AND Ollama is enabled
    if USE_OLLAMA:
        print("🟢 USE_OLLAMA=true → Attempting Ollama (secondary)...")
        answer, success = generate_answer_local(question, context_chunks)
        if success:
            return answer
    else:
        print("⚪ USE_OLLAMA=false → Ollama fallback disabled")

    # If both fail or Ollama is disabled
    return (
        "Sorry, I couldn't generate an answer right now. "
        "Groq failed and Ollama is not enabled. "
        "Check logs and set USE_OLLAMA=true if you want local fallback."
    )