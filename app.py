import streamlit as st
import pandas as pd
import plotly.express as px
import time

from core.database import *
from core.sentiment import StressAnalyzer
from core.chatbot import WellnessChatbot

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="StressGuard AI",
    layout="wide",
    page_icon="🌿"
)

st.markdown("""
<style>
.metric-box {
    background-color: #f8fafc;
    padding: 15px;
    border-radius: 10px;
}
.block-container {
    padding-top: 2rem;
}
</style>
""", unsafe_allow_html=True)
# =====================================================
# LOAD MODELS
# =====================================================

@st.cache_resource
def load_models():
    return StressAnalyzer(), WellnessChatbot()

analyzer, chatbot = load_models()

init_db()

if "user" not in st.session_state:
    st.session_state.user = None

# =====================================================
# AUTH SCREEN
# =====================================================

def auth_screen():
    st.title("🌿 StressGuard AI")
    st.caption("AI-Powered Employee Wellness Assistant")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            user = login_user(username, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        username = st.text_input("New Username")
        password = st.text_input("New Password", type="password")
        role = st.selectbox("Role", ["employee", "manager", "admin"])

        if st.button("Register"):
            if register_user(username, password, role):
                st.success("Registered successfully")
            else:
                st.error("Username already exists")

#=============EMPLOYEE DASHBOARD=====================

def employee_dashboard():
    user = st.session_state.user

    st.markdown(f"## Welcome, {user['username']} 🌿")
    st.caption("Your 24/7 AI Wellness Coach")
    st.info("""
         StressGuard AI analyzes emotional reflections using AI
         and tracks stress trends to prevent burnout.
        """)
    
    logs = get_user_logs(user["id"])
    df = pd.DataFrame(logs, columns=["timestamp","score"]) if logs else pd.DataFrame()

    menu = st.radio(
        "Navigation",
        ["Dashboard", "Wellness Chat", "History"],
        horizontal=True
    )

    # ===================== DASHBOARD =====================
    if menu == "Dashboard":

        if df.empty:
            st.info("No check-ins yet.")
        else:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            current = df["score"].iloc[0]
            weekly = get_weekly_stress(user["id"])
            monthly = get_monthly_stress(user["id"])

            col1, col2, col3 = st.columns(3)
            col1.metric("Current Stress", f"{current}/100")
            col2.metric("Weekly Avg", weekly if weekly else "N/A")
            col3.metric("Monthly Avg", monthly if monthly else "N/A")

            fig = px.line(df, x="timestamp", y="score")
            st.plotly_chart(fig, use_container_width=True)

    # ===================== WELLNESS CHAT =====================
    elif menu == "Wellness Chat":

        st.subheader("💬 Talk to StressGuard AI")

        # Load chat history ONCE
        if "chat_loaded" not in st.session_state:
            st.session_state.chat_messages = get_chat_history(user["id"]) or []
            st.session_state.chat_loaded = True

        # Display chat
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["message"])

        user_input = st.chat_input("Share what's on your mind...")

        if user_input and user_input.strip():

            # Prevent duplicate processing
            if st.session_state.get("last_message") == user_input:
                st.stop()

            st.session_state.last_message = user_input

            # Show user message immediately
            st.session_state.chat_messages.append(
                {"role": "user", "message": user_input}
            )

            # Analyze stress
            score = analyzer.analyze_text(user_input)

            # Generate AI response
            # Generate AI response (WITH LIMITED MEMORY)
            reply = chatbot.get_response(
            user_message=user_input,
            stress_score=score,
            history=st.session_state.chat_messages
             )

            # Show assistant message
            st.session_state.chat_messages.append(
                {"role": "assistant", "message": reply}
            )

            # Save to database
            save_chat_message(user["id"], "user", user_input)
            save_chat_message(user["id"], "assistant", reply)
            save_stress_log(user["id"], user_input, score)

            if score >= 75:
                create_alert(user["id"], score)

            st.rerun()

    # ===================== HISTORY =====================
    elif menu == "History":

        if df.empty:
            st.info("No history available.")
        else:
            st.dataframe(df, use_container_width=True)
            st.download_button(
                "Download CSV",
                df.to_csv(index=False),
                "stress_history.csv"
            )

# =====================================================
# MANAGER DASHBOARD
# =====================================================

def manager_dashboard():

    user = st.session_state.user

    st.title("🏢 Enterprise Team Wellness Overview")

    st.write("Logged Manager ID:", user["id"])
    st.write("Logged Manager Username:", user["username"])
    st.info("""
        This dashboard provides real-time team wellness insights,
        burnout detection, and alert intelligence.
    """)

    # =====================================================
    # BUILD TEAM
    # =====================================================
   

    st.subheader("👥 Build Your Team")

    available = get_available_employees(user["id"])

    if available:

         df_available = pd.DataFrame([dict(row) for row in available])

         selected = st.multiselect(
              "Select Employees to Add",
             df_available["username"].tolist()
            )

         if st.button("Add To My Team", use_container_width=True):

            if not selected:
                  st.warning("Please select at least one employee.")
            else:
                 for name in selected:

                     emp_row = df_available[df_available["username"] == name]

                     if emp_row.empty:
                         st.error("Employee not found.")
                         continue

                     emp_id = emp_row["id"].values[0]
                     
                     success = assign_employee(emp_id, user["id"])

                     if success:
                            st.success("Employee added successfully!")
                     else:
                             st.warning("Employee already in your team.")
                 st.success("Employees added successfully ✅")
                 st.rerun()
  
    else:
          st.info("No available employees to assign.")
    # =====================================================
    # MY TEAM MEMBERS
    # =====================================================

    st.subheader("👥 My Team Members")

    team_members = get_manager_team_members(user["id"])

    if team_members:
         team_df = pd.DataFrame(team_members, columns=["id", "username"])
         st.dataframe(team_df[["username"]], use_container_width=True)
    else:
         st.info("No employees in your team yet.")    

    # =====================================================
    # TEAM LOGS
    # =====================================================

    logs = get_manager_team_logs(user["id"])

    if not logs:
        st.info("No team reflections yet.")
        return

    df = pd.DataFrame(logs, columns=["username","timestamp","score"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # =====================================================
    # TEAM METRICS
    # =====================================================

    st.subheader("📊 Team Metrics")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Reflections", len(df))
    col2.metric("Avg Team Stress", round(df["score"].mean(), 1))
    col3.metric("High Risk Employees",
                len(df[df["score"] >= 70]["username"].unique()))

    # =====================================================
    # STRESS TREND
    # =====================================================

    st.subheader("📈 Stress Trend")

    fig = px.line(df, x="timestamp", y="score", color="username")
    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # BURNOUT TABLE
    # =====================================================

    st.subheader("🔥 Burnout Risk Employees")

    risk_df = df[df["score"] >= 70]

    if not risk_df.empty:
        st.dataframe(
            risk_df.sort_values("score", ascending=False),
            use_container_width=True
        )
    else:
        st.success("No high burnout risk employees 🎉")

    # =====================================================
    # ALERTS
    # =====================================================

    st.subheader("🚨 Active Alerts")

    alerts = get_manager_team_alerts(user["id"])

    if alerts:
        alert_df = pd.DataFrame(
            alerts,
            columns=["username","timestamp","score","severity","escalation_level"]
        )
        st.dataframe(alert_df, use_container_width=True)
    else:
        st.success("No active alerts.")

    # =====================================================
    # EXECUTIVE SUMMARY
    # =====================================================

    st.subheader("🧠 Executive Wellness Summary")

    avg_stress = round(df["score"].mean(), 1)
    highest_stress = df["score"].max()
    high_risk_count = len(risk_df["username"].unique())

    if avg_stress < 40:
        summary = "Team is emotionally stable with low overall stress levels."
    elif avg_stress < 70:
        summary = "Team shows moderate stress. Recommend check-ins and workload balancing."
    else:
        summary = "High overall stress detected. Immediate managerial intervention recommended."

    summary += f"\n\n• Average Stress: {avg_stress}"
    summary += f"\n• Highest Stress: {highest_stress}"
    summary += f"\n• Employees Above 70: {high_risk_count}"

    st.info(summary)
# =====================================================
# ADMIN DASHBOARD
# =====================================================

def admin_dashboard():
    st.title("🌎 Organization Intelligence Panel")
    st.info("""
            Organization-wide emotional intelligence monitoring system.
            """)
    logs = fetch_all_logs()

    if not logs:
        st.info("No data available.")
        return

    df = pd.DataFrame(logs, columns=["timestamp","username","text","score"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    st.subheader("📊 Organization Metrics")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Reflections", len(df))
    col2.metric("Organization Avg Stress", round(df["score"].mean(),1))
    col3.metric("Burnout Risk Users",
                len(df[df["score"] >= 70]["username"].unique()))

    fig = px.box(df, x="username", y="score")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🔥 High Risk Employees")

    risk_df = df[df["score"] >= 75]
    if not risk_df.empty:
        st.dataframe(risk_df.sort_values("score", ascending=False),
                     use_container_width=True)
    else:
        st.success("No critical alerts.")

# =====================================================
# ROUTER
# =====================================================

if st.session_state.user is None:
    auth_screen()
    st.stop()

with st.sidebar:
    st.markdown("### 🌿 StressGuard AI")
    st.write(st.session_state.user["username"])
    st.caption(st.session_state.user["role"].capitalize())

    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()

role = st.session_state.user["role"]

if role == "employee":
    employee_dashboard()
elif role == "manager":
    manager_dashboard()
elif role == "admin":
    admin_dashboard()

st.markdown("---")
st.caption("StressGuard AI © 2026 | Enterprise Emotional Intelligence Platform")