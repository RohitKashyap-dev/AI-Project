import json
import os
import streamlit as st
import requests
import traceback
import time

from scam_detector.classifier import classify_message
from scam_detector.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Streamlit Scam Detector App Started")


st.set_page_config(page_title="Scam Detector", layout="wide")
st.title("Scam Detector")

def _get_api_default() -> str:
    try:
        return st.secrets["API_URL"]
    except Exception:
        return os.getenv("API_URL", "http://localhost:8000")


API_DEFAULT = _get_api_default()
if "token" not in st.session_state:
    st.session_state.token = None
if "example" not in st.session_state:
    st.session_state.example = ""

# hidden API URL (no visible input)
API_URL = st.session_state.get("api_url", API_DEFAULT)


def _complete_login(success_message: str) -> None:
    """Store auth state and trigger a rerun so the main app becomes visible."""
    st.success(success_message)
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.info("Login successful — please refresh the page to continue.")


# If not logged in, show a focused login page before exposing the analyzer
if not st.session_state.token:
    st.header("Please sign in to continue")
    # API URL is configured in session or defaults; not shown here
    API_URL = st.session_state.get("api_url", API_DEFAULT)

    with st.form("login_page"):
        login_user = st.text_input("Username")
        login_pass = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        if submit:
                try:
                    resp = requests.post(f"{API_URL}/token", json={"username": login_user, "password": login_pass}, timeout=5)
                    if resp.ok:
                        access_token = resp.json().get("access_token")
                        if access_token:
                            st.session_state.token = access_token
                            _complete_login("Login successful")
                        else:
                            st.error("Login failed: no access token received")
                    else:
                        st.error("Login failed")
                        # persist response text for debugging
                        with open('logs/streamlit_ui_errors.log', 'a') as f:
                            f.write(f"LOGIN_FAILED: status={resp.status_code} text={resp.text}\n")
                except Exception as exc:
                    st.error("Login error")
                    logger.error("Login error: %s", exc, exc_info=True)
                    with open('logs/streamlit_ui_errors.log', 'a') as f:
                        f.write('LOGIN_EXCEPTION:\n')
                        f.write(traceback.format_exc())

    st.markdown("---")
    if st.button("Demo Login (admin)"):
        try:
            t = requests.post(f"{API_URL}/token", json={"username": "admin", "password": "password"}, timeout=5)
            if t.ok:
                access_token = t.json().get("access_token")
                if access_token:
                    st.session_state.token = access_token
                    _complete_login("Demo login succeeded")
                else:
                    st.error("Demo login failed: no access token received")
            else:
                st.error("Demo login failed")
                with open('logs/streamlit_ui_errors.log', 'a') as f:
                    f.write(f"DEMO_LOGIN_FAILED: status={t.status_code} text={t.text}\n")
        except Exception as exc:
            st.error("Demo login error")
            logger.error("Demo login error: %s", exc, exc_info=True)
            with open('logs/streamlit_ui_errors.log', 'a') as f:
                f.write('DEMO_LOGIN_EXCEPTION:\n')
                f.write(traceback.format_exc())

    # Only halt rendering if still not authenticated — allow continuation when login succeeded
    if not st.session_state.token:
        st.stop()

with st.sidebar:
    st.header("Connection")
    # API URL is configured in session or defaults; hidden from UI
    API_URL = st.session_state.get("api_url", API_DEFAULT)

    st.divider()
    st.subheader("Examples")
    if st.button("Prize Scam Example"):
        st.session_state.example = "Congratulations! You have won ₹10 Lakhs. Pay a small processing fee to claim your prize."
    if st.button("Legit Example"):
        st.session_state.example = "Hi students, tomorrow's class will start at 10 AM in Room 201."
    if st.button("Phishing Example"):
        st.session_state.example = "Your parcel is waiting. Click this link to track it."

    st.markdown("---")
    st.markdown("**How to use**\n\n1. Login (required)  2. Paste message  3. Click Analyze")


col_main, col_side = st.columns([3, 1])

with col_main:
    st.subheader("Enter Message to Analyze")
    with st.form("analyze_form"):
        model_name = st.selectbox("Model", ["gemini-3.1-flash-lite", "gemini-2.0-flash", "gemini-1.5-pro"])
        user_message = st.text_area("Paste the SMS or message here:", placeholder="Enter the message you want to check...", height=160, value=st.session_state.get("example", ""))
        col_a, col_b = st.columns([1, 3])
        with col_a:
            analyze_btn = st.form_submit_button("Analyze Message")
        with col_b:
            run_local_checkbox = st.checkbox("Analyze locally if API unavailable", value=True)

    # handle demo-run trigger from sidebar
    if st.session_state.pop("run_demo", False):
        user_message = st.session_state.get("example", user_message)
        analyze_btn = True

    if analyze_btn:
        if not user_message or not user_message.strip():
            st.warning("Please enter a message to analyze.")
        else:
            with st.spinner("Analyzing message..."):
                parsed_response = None
                try:
                    # prefer API if token present and API reachable
                    if st.session_state.token:
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        try:
                            resp = requests.post(f"{API_URL}/analyze", json={"message": user_message, "model_name": model_name}, headers=headers, timeout=20)
                        except Exception:
                            resp = None
                        if resp and resp.ok:
                            payload = resp.json()
                            parsed_json = payload.get("result") if isinstance(payload, dict) and "result" in payload else payload
                        else:
                            parsed_json = None
                    else:
                        parsed_json = None

                    if parsed_json is None and run_local_checkbox:
                        parsed_response = classify_message(user_message, model_name=model_name)
                    elif parsed_json is not None:
                        class R:
                            pass
                        parsed_response = R()
                        parsed_response.is_scam = parsed_json.get("is_scam")
                        parsed_response.scam_type = parsed_json.get("scam_type")
                        parsed_response.confidence = parsed_json.get("confidence") or 0.0
                        parsed_response.reply = parsed_json.get("reply") or ""
                        parsed_response.indicators = parsed_json.get("indicators") or []
                        parsed_response.recommended_action = parsed_json.get("recommended_action") or ""

                    if parsed_response is None:
                        st.error("Failed to get analysis from API and local analyzer disabled.")
                    else:
                        # Clear previous example to avoid accidental reuse
                        st.session_state.example = ""
                        # Results card
                        with st.container():
                            st.markdown("### Analysis Result")
                            cols = st.columns([1, 1, 1])
                            with cols[0]:
                                if parsed_response.is_scam == "Scam":
                                    st.error(f"**Classification:** {parsed_response.is_scam}")
                                elif parsed_response.is_scam == "Not Scam":
                                    st.success(f"**Classification:** {parsed_response.is_scam}")
                                else:
                                    st.warning(f"**Classification:** {parsed_response.is_scam}")
                            with cols[1]:
                                st.info(f"**Scam Type:** {parsed_response.scam_type}")
                            with cols[2]:
                                st.metric("Confidence", f"{int(parsed_response.confidence * 100)}%")

                            st.markdown("---")
                            left, right = st.columns([2, 1])
                            with left:
                                st.subheader("Explanation")
                                st.write(parsed_response.reply)
                                if parsed_response.indicators:
                                    st.write("**Indicators:**")
                                    for ind in parsed_response.indicators:
                                        st.write(f"• {ind}")
                            with right:
                                st.subheader("Action")
                                st.write(parsed_response.recommended_action or "—")
                                # provide JSON download
                                result_json = json.dumps({
                                    "is_scam": parsed_response.is_scam,
                                    "scam_type": parsed_response.scam_type,
                                    "confidence": parsed_response.confidence,
                                    "reply": parsed_response.reply,
                                    "indicators": parsed_response.indicators,
                                    "recommended_action": parsed_response.recommended_action,
                                }, indent=2)
                                st.download_button("Download JSON", data=result_json, file_name="analysis.json", mime="application/json")
                                st.text_area("Raw JSON", value=result_json, height=200)

                except Exception as exc:
                    st.error("Error analyzing message")
                    logger.error("Error during analysis: %s", exc, exc_info=True)

with col_side:
    st.subheader("Quick Actions")
    st.write("Use the sidebar to login, run the demo, or load examples.")

