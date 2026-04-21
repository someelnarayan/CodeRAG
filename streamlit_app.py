import streamlit as st
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Code RAG Assistant", layout="centered")

# ✅ FIXED: hardcode your Render URL as default
BASE_URL = os.getenv("BASE_URL", "https://coderag-2.onrender.com")

# =========================
# SESSION STATE
# =========================
if "token" not in st.session_state:
    st.session_state.token = None

if "repo" not in st.session_state:
    st.session_state.repo = None

if "ingestion_complete" not in st.session_state:
    st.session_state.ingestion_complete = False


def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def get_repo_status(repo_url):
    try:
        res = requests.get(
            f"{BASE_URL}/status",
            params={"repo_url": repo_url},
            headers=get_headers()
        )
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {"status": "unknown", "progress": 0}


# =========================
# LOGIN / SIGNUP
# =========================
if not st.session_state.token:
    st.title("Code RAG Assistant")
    st.subheader("Login or Signup to continue")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login", use_container_width=True):
            try:
                res = requests.post(
                    f"{BASE_URL}/auth/login",
                    data={"username": username, "password": password}
                )
                if res.status_code == 200:
                    st.session_state.token = res.json()["access_token"]
                    st.success("Login successful.")
                    st.rerun()
                else:
                    st.error(res.json().get("detail", "Login failed."))
            except Exception as e:
                st.error(f"Cannot connect to backend: {e}")

    with col2:
        if st.button("Signup", use_container_width=True):
            try:
                res = requests.post(
                    f"{BASE_URL}/auth/signup",
                    params={"username": username, "password": password}
                )
                if res.status_code == 200:
                    st.success("Account created. Please login.")
                else:
                    st.error(res.json().get("detail", "Signup failed."))
            except Exception as e:
                st.error(f"Cannot connect to backend: {e}")


# =========================
# INGEST REPO
# =========================
elif not st.session_state.repo:
    st.title("Ingest Repository")
    st.caption("Enter a public GitHub repository URL to get started.")

    repo_url = st.text_input("GitHub Repository URL")

    if st.button("Start Ingestion", use_container_width=True):
        if not repo_url.strip():
            st.warning("Please enter a repository URL.")
        else:
            res = requests.post(
                f"{BASE_URL}/ingest",
                json={"repo_url": repo_url},
                headers=get_headers()
            )
            if res.status_code == 200:
                st.session_state.repo = repo_url
                st.session_state.ingestion_complete = False
                st.rerun()
            else:
                st.error(res.json().get("detail", "Ingestion failed to start."))

    if st.button("Logout", use_container_width=True):
        st.session_state.token = None
        st.session_state.repo = None
        st.session_state.ingestion_complete = False
        st.rerun()


# =========================
# INGESTION PROGRESS + ASK
# =========================
else:
    st.title("Code RAG Assistant")
    st.caption(f"Repository: `{st.session_state.repo}`")

    if not st.session_state.ingestion_complete:
        status_data = get_repo_status(st.session_state.repo)
        status = status_data.get("status")
        progress = status_data.get("progress", 0)

        if status == "completed":
            st.session_state.ingestion_complete = True

        elif status == "failed":
            st.error("Repository ingestion failed. Please go back and try again.")
            if st.button("Go Back"):
                st.session_state.repo = None
                st.session_state.ingestion_complete = False
                st.rerun()

        else:
            st.info("Ingestion in progress. Please wait...")
            progress_bar = st.progress(progress / 100)
            status_text = st.empty()
            status_text.caption(f"Progress: {progress}%")

            while True:
                time.sleep(2)
                status_data = get_repo_status(st.session_state.repo)
                status = status_data.get("status")
                progress = status_data.get("progress", 0)

                progress_bar.progress(min(progress / 100, 1.0))
                status_text.caption(f"Progress: {progress}%")

                if status == "completed":
                    st.session_state.ingestion_complete = True
                    st.success("Ingestion complete. You can now ask questions.")
                    time.sleep(1)
                    st.rerun()
                    break

                elif status == "failed":
                    st.error("Ingestion failed. Please go back and try again.")
                    break

    # =========================
    # ASK SECTION
    # =========================
    if st.session_state.ingestion_complete:
        st.success("Repository is ready. Ask your questions below.")
        st.divider()

        question = st.text_input("Enter your question about the repository")

        if st.button("Ask", use_container_width=True):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                res = requests.post(
                    f"{BASE_URL}/ask",
                    json={
                        "repo_url": st.session_state.repo,
                        "question": question
                    },
                    headers=get_headers()
                )

                if res.status_code == 200:
                    task_id = res.json()["task_id"]
                    status_placeholder = st.empty()

                    while True:
                        result = requests.get(
                            f"{BASE_URL}/result/{task_id}",
                            headers=get_headers()
                        ).json()

                        status_placeholder.info(result.get("message", "Generating response..."))

                        if result["status"] == "completed":
                            status_placeholder.empty()
                            st.success("Response generated successfully.")
                            st.write(result["answer"])
                            if result.get("source"):
                                st.caption(f"Source: {result['source']}")
                            break

                        elif result["status"] == "failed":
                            status_placeholder.empty()
                            st.error("Failed to generate a response.")
                            if result.get("answer"):
                                st.write(result["answer"])
                            break

                        time.sleep(1)

                else:
                    st.error(res.json().get("detail", "Request failed."))

    # =========================
    # SIDEBAR CONTROLS
    # =========================
    with st.sidebar:
        st.subheader("Session")
        st.write(f"Repository: `{st.session_state.repo}`")

        if st.button("Change Repository"):
            st.session_state.repo = None
            st.session_state.ingestion_complete = False
            st.rerun()

        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.repo = None
            st.session_state.ingestion_complete = False
            st.rerun()