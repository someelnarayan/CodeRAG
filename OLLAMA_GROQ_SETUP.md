# Ollama + Groq Setup - Simple Guide 🚀

## What's This About?

Your project can use **two different AI models**:
- **Groq** - Cloud-based, fast, costs money
- **Ollama** - Runs on your computer, free, offline

We're setting it up so Ollama runs first (cheap + fast), and if it's slow, automatically switch to Groq (backup plan).

---

## Step 1: Start Ollama (Local AI Model)

Ollama runs in Docker. Just run this:

```bash
# This starts the Ollama service
docker-compose up -d

# Wait 30 seconds, then download the AI model (~7GB)
# This takes 5-10 minutes depending on your internet
docker exec ollama-llama31 ollama pull llama3.1:8b-instruct-q4_K_M

# Check if it worked
docker exec ollama-llama31 ollama list
```

That's it! Ollama is running on `http://localhost:11434`

---

## Step 2: Update .env File

Open `.env` and make sure these are set:

```bash
# Which AI to use?
USE_GROQ=true           # true = try Ollama first, then Groq

# Cloud AI (for fallback)
GROQ_API_KEY=your_actual_api_key_here

# Local AI (on your computer)
OLLAMA_BASE_URL=http://localhost:11434
```

That's it. Rest of the settings are already good.

---

## Step 3: Install & Start Your App

```bash
# Install new dependencies (slowapi for rate limiting)
pip install -r requirements_backend.txt

# Start the server
python -m uvicorn app.main:app --reload
```

Watch the logs - you'll see colored messages like:

```
🔵 OLLAMA: Attempting inference (2s timeout)...
✅ Ollama success in 0.45s
```

If Ollama is slow, it automatically switches:

```
⏱️  OLLAMA TIMEOUT: took 2.05s (> 2s limit)
🔴 GROQ: Attempting cloud inference...
✅ GROQ SUCCESS: 0.82s
```

---

## Step 4: Test It

Use Postman or curl to test:

```bash
# First, login to get a token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=password"

# Copy the token from response, then ask a question
curl -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url":"https://github.com/owner/repo.git",
    "question":"What does main.py do?"
  }'

# You'll get a task_id back, check status with:
curl http://localhost:8000/result/TASK_ID_HERE \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## How Does It Work? (Simple Explanation)

```
User Asks Question
    ↓
Check Cache (super fast - 0ms!)
    ↓ (if not in cache)
Find relevant code chunks (2 seconds)
    ↓
Try Local Ollama FIRST (free!)
    ↓ (if it's slow or offline)
Use Groq Cloud (paid backup)
    ↓
Save answer in cache
    ↓
Return answer to user
```

**Why this design is smart:**
- Ollama saves money (free, runs locally)
- Groq ensures it never times out (reliable backup)
- Cache makes repeat questions instant

---

## Problems & Fixes

### ❌ "Connection refused" when I ask questions
**What's wrong:** Ollama container isn't running

**How to fix:**
```bash
docker-compose up -d
docker exec ollama-llama31 ollama list
```

---

### ❌ "GROQ_API_KEY not set" error
**What's wrong:** You didn't add your Groq API key to .env

**How to fix:**
1. Get free key from https://console.groq.com
2. Add to `.env`:
```bash
GROQ_API_KEY=your_actual_key_here
```

---

### ❌ "Rate limit exceeded" message
**What's wrong:** You're making too many requests at once

**The limit:** 10 questions per minute (hardcoded for safety)

**How to fix:** Just wait a minute and try again 😊

---

### ❌ Model download failed
**What's wrong:** Internet issue or storage problem

**How to fix:**
```bash
# Check if model is actually there
docker exec ollama-llama31 ollama list

# If not there, download again (takes 5-15 mins)
docker exec ollama-llama31 ollama pull llama3.1:8b-instruct-q4_K_M
```

---

## Want a Smaller/Faster Model?

If your computer is weak, use a smaller model:

```bash
# Light version - 3.3GB, super fast
docker exec ollama-llama31 ollama pull llama3.1:8b-instruct-q2_K

# Heavy version - 8.7GB, smarter answers
docker exec ollama-llama31 ollama pull llama3.1:8b-instruct-q5_K_M
```

Then restart your app and it'll use the new model automatically.

---

## Stop & Clean Up

If you need to stop everything:

```bash
# Stop Ollama container
docker-compose down

# Delete downloaded models (frees ~7GB)
docker volume rm docker_ollama_data

# Start fresh next time
docker-compose up -d
docker exec ollama-llama31 ollama pull llama3.1:8b-instruct-q4_K_M
```

---

## Debug Mode

Want to see what's happening? Run the server and watch the logs:

```bash
python -m uvicorn app.main:app --reload
```

You'll see stuff like:
```
✅ CACHE HIT: 0.2ms - returning immediately
🔵 OLLAMA: Attempting inference (2s timeout)...
   Retrieved 5 chunks in 0.45s
   💾 Cached in 15.3ms
Done!
```

---

**That's it! Pretty simple right?** 🎉

If something breaks, the errors are usually clear. Just check the steps above!
