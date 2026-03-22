import streamlit as st
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="AI Assistant")

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

# =========================
# SESSION STATE
# =========================
if "token" not in st.session_state:
    st.session_state.token = None

if "repo" not in st.session_state:
    st.session_state.repo = None


# =========================
# LOGIN / SIGNUP
# =========================
if not st.session_state.token:
    st.title("Login / Signup")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    # LOGIN
    with col1:
        if st.button("Login"):
            res = requests.post(
                f"{BASE_URL}/auth/login",
                data={
                    "username": username,
                    "password": password
                }
            )

            if res.status_code == 200:
                token = res.json()["access_token"]
                st.session_state.token = token
                st.success("Login successful")
                st.rerun()
            else:
                st.error(res.text)

    # SIGNUP
    with col2:
        if st.button("Signup"):
            res = requests.post(
                f"{BASE_URL}/auth/signup",
                params={
                    "username": username,
                    "password": password
                }
            )

            if res.status_code == 200:
                st.success("Signup successful. Please login.")
            else:
                st.error(res.text)


# =========================
# INGEST REPO
# =========================
elif not st.session_state.repo:
    st.title("Ingest Repository")

    repo_url = st.text_input("Enter GitHub Repo URL")

    if st.button("Ingest"):
        res = requests.post(
            f"{BASE_URL}/ingest",
            json={"repo_url": repo_url},
            headers={
                "Authorization": f"Bearer {st.session_state.token}"
            }
        )

        if res.status_code == 200:
            st.success("Repository ingestion started")
            st.session_state.repo = repo_url
            st.rerun()
        else:
            st.error(res.text)


# =========================
# ASK QUESTION
# =========================
else:
    st.title("Ask Questions")

    question = st.text_input("Ask something about the repository")

    if st.button("Ask"):
        res = requests.post(
            f"{BASE_URL}/ask",
            json={
                "repo_url": st.session_state.repo,
                "question": question
            },
            headers={
                "Authorization": f"Bearer {st.session_state.token}"
            }
        )

        if res.status_code == 200:
            task_id = res.json()["task_id"]

            status_placeholder = st.empty()

            # 🔁 POLLING LOOP
            while True:
                result = requests.get(
                    f"{BASE_URL}/result/{task_id}",
                    headers={
                        "Authorization": f"Bearer {st.session_state.token}"
                    }
                ).json()

                # 🔥 Professional status message
                status_placeholder.info(result.get("message", "Generating response..."))

                if result["status"] == "completed":
                    status_placeholder.empty()
                    st.success("Response generated successfully.")
                    st.write(result["answer"])
                    break

                elif result["status"] == "failed":
                    status_placeholder.empty()
                    st.error("Request failed.")
                    st.write(result.get("answer"))
                    break

                time.sleep(1)

        else:
            st.error(res.text)

    # =========================
    # LOGOUT
    # =========================
    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.repo = None
        st.rerun()