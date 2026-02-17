import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from core.database import (
    init_db,
    register_user,
    login_user,
    save_stress_log,
    get_user_logs,
    fetch_all_logs,
    get_manager_team_logs,
    assign_employee,
    get_unassigned_employees,
    create_alert,
    get_manager_team_alerts,
    get_all_alerts,
    get_weekly_stress,
    get_monthly_stress,
    get_burnout_risk_users
)

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

# =====================================================
# LIGHT WELLNESS THEME
# =====================================================

st.markdown("""
<style>

html, body, [class*="css"]  {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background-color: #F8FAFC;
    color: #1F2937;
}

section[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid #E5E7EB;
}

h1 {
    font-weight: 600;
    color: #111827;
}

h2, h3 {
    font-weight: 500;
    color: #1F2937;
}

.stButton>button {
    background-color: #10B981;
    color: white;
    border-radius: 8px;
    padding: 8px 18px;
    border: none;
    font-weight: 500;
}

.stButton>button:hover {
    background-color: #059669;
}

textarea {
    background-color: #FFFFFF !important;
    border-radius: 8px !important;
    border: 1px solid #E5E7EB !important;
    color: #1F2937 !important;
}

[data-testid="metric-container"] {
    background-color: #FFFFFF;
    border-radius: 12px;
    padding: 12px;
    border: 1px solid #E5E7EB;
}

[data-testid="stDataFrame"] {
    border-radius: 10px;
    border: 1px solid #E5E7EB;
}

hr {
    border: none;
    height: 1px;
    background: #E5E7EB;
    margin: 24px 0;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# INIT
# =====================================================

init_db()
analyzer = StressAnalyzer()
chatbot = WellnessChatbot()

if "user" not in st.session_state:
    st.session_state.user = None


# =====================================================
# HELPERS
# =====================================================

def stress_color(score):
    if score >= 75:
        return "Needs Attention"
    elif score >= 50:
        return "Moderate"
    else:
        return "Stable"


# =====================================================
# AUTH SCREEN
# =====================================================

def auth_screen():
    st.title("StressGuard AI")
    st.caption("Employee Emotional Wellness Platform")

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
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        role = st.selectbox("Role", ["employee", "manager", "admin"])

        if st.button("Register"):
            success = register_user(new_user, new_pass, role)
            if success:
                st.success("User registered successfully")
            else:
                st.error("Username already exists")


# =====================================================
# EMPLOYEE DASHBOARD
# =====================================================

def show_employee_dashboard():
    user = st.session_state.user

    st.title(f"Welcome, {user['username']}")
    st.caption("Track your emotional wellbeing and maintain balance.")

    st.markdown("---")

    logs = get_user_logs(user["id"])

    if logs:
        df = pd.DataFrame(logs, columns=["timestamp", "user_text", "stress_score"])
    else:
        df = pd.DataFrame(columns=["timestamp", "user_text", "stress_score"])

    # ================= METRICS =================
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        current = df["stress_score"].iloc[-1]
        avg = round(df["stress_score"].mean(), 1)
        peak = df["stress_score"].max()

        col1, col2, col3 = st.columns(3)

        # -------- Gauge --------
        with col1:
            gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=current,
                number={'suffix': "/100"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#10B981"},
                    'bgcolor': "#FFFFFF",
                }
            ))

            gauge.update_layout(
                height=250,
                paper_bgcolor="#F8FAFC",
                font={'color': "#1F2937"}
            )

            st.plotly_chart(gauge, use_container_width=True)

        col2.metric("Average Stress", avg)
        col3.metric("Peak Stress", peak)

        # -------- Emotional Guidance --------
        if current < 40:
            st.success("You appear emotionally balanced today.")
        elif current < 70:
            st.warning("Your stress level is slightly elevated. A gentle pause may help.")
        else:
            st.warning("Your stress level is higher than usual. Consider rest or support.")

        # =====================================================
        # WEEKLY INSIGHT SUMMARY
        # =====================================================

        if len(df) >= 2:
            st.markdown("---")
            st.subheader("Weekly Wellness Insight")

            weekly_df = df.sort_values("timestamp").tail(7)
            weekly_avg = round(weekly_df["stress_score"].mean(), 1)

            first_score = weekly_df["stress_score"].iloc[0]
            last_score = weekly_df["stress_score"].iloc[-1]

            if last_score > first_score + 5:
                trend = "Increasing"
                message = "Your stress levels have gradually increased this week."
            elif last_score < first_score - 5:
                trend = "Decreasing"
                message = "Your stress levels have improved compared to earlier this week."
            else:
                trend = "Stable"
                message = "Your stress levels have remained relatively stable this week."

            st.markdown(f"""
            <div style="
                background-color:#FFFFFF;
                padding:20px;
                border-radius:12px;
                border:1px solid #E5E7EB;
                margin-top:10px;
            ">
                <h4 style="margin-bottom:10px; color:#111827;">
                    Weekly Summary
                </h4>
                <p style="margin:5px 0; color:#374151;">
                    • Average Stress This Week: <b>{weekly_avg}/100</b>
                </p>
                <p style="margin:5px 0; color:#374151;">
                    • Trend: <b>{trend}</b>
                </p>
                <p style="margin-top:12px; color:#4B5563;">
                    {message}
                </p>
            </div>
            """, unsafe_allow_html=True)

    
        # ================= DAILY REFLECTION =================

    st.markdown("---")
    st.subheader("Daily Reflection")

    user_text = st.text_area(
        "",
        placeholder="Describe how you are feeling today...",
        height=120
    )

    if st.button("Analyze"):
        if user_text.strip():
            score = analyzer.analyze_text(user_text)
            reply = chatbot.get_response(user_text)

            save_stress_log(user["id"], user_text, score)

            if score >= 75:
                create_alert(user["id"], score)

            # Store in session state (IMPORTANT)
            st.session_state.last_score = score
            st.session_state.last_reply = reply

        else:
            st.warning("Please enter your thoughts.")

    # Show result if available
    if "last_score" in st.session_state:
        st.metric("Stress Score", f"{st.session_state.last_score}/100")
        st.info(st.session_state.last_reply)

    # ================= TREND CHART =================

    if not df.empty:
        st.markdown("---")
        st.subheader("Stress Trend")

        fig = px.line(df, x="timestamp", y="stress_score")
        fig.update_traces(line_color="#10B981")
        fig.update_layout(
            height=350,
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#F8FAFC",
            font_color="#1F2937"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.subheader("History")
        st.dataframe(
            df.sort_values("timestamp", ascending=False),
            use_container_width=True
        )


# =====================================================
# MANAGER DASHBOARD
# =====================================================

def show_manager_dashboard():
    user = st.session_state.user

    st.title("Team Wellness Overview")
    st.markdown("---")

    logs = get_manager_team_logs(user["id"])

    if logs:
        df = pd.DataFrame(logs, columns=["username", "timestamp", "stress_score"])

        col1, col2, col3 = st.columns(3)
        col1.metric("Team Check-ins", len(df))
        col2.metric("Average Stress", round(df["stress_score"].mean(), 1))
        col3.metric("Elevated Risk Cases", len(df[df["stress_score"] >= 75]))

        fig = px.line(df, x="timestamp", y="stress_score", color="username")
        fig.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#F8FAFC",
            font_color="#1F2937"
        )

        st.plotly_chart(fig, use_container_width=True)

        df["Status"] = df["stress_score"].apply(stress_color)
        st.dataframe(df, use_container_width=True)

    alerts = get_manager_team_alerts(user["id"])
    if alerts:
        st.subheader("Active Alerts")
        alert_df = pd.DataFrame(alerts,
                                columns=["username", "timestamp", "stress_score"])
        st.dataframe(alert_df)


# =====================================================
# ADMIN DASHBOARD
# =====================================================

def show_admin_dashboard():
    st.title("Organization Wellness Overview")
    st.markdown("---")

    logs = fetch_all_logs()

    if logs:
        df = pd.DataFrame(
            logs,
            columns=["timestamp", "username", "user_text", "stress_score"]
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Check-ins", len(df))
        col2.metric("Average Stress", round(df["stress_score"].mean(), 1))
        col3.metric("Highest Stress Recorded", df["stress_score"].max())

        fig = px.bar(df, x="username", y="stress_score")
        fig.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#F8FAFC",
            font_color="#1F2937"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df, use_container_width=True)

    burnout = get_burnout_risk_users()
    if burnout:
        st.subheader("Burnout Risk Employees")
        burnout_df = pd.DataFrame(burnout,
                                  columns=["username", "avg_stress"])
        st.dataframe(burnout_df)


# =====================================================
# ROUTER
# =====================================================

if st.session_state.user is None:
    auth_screen()
    st.stop()

user = st.session_state.user
role = user["role"]

if role == "user":
    role = "employee"

with st.sidebar:
    st.markdown("### StressGuard AI")
    st.markdown("---")
    st.write(user["username"])
    st.caption(f"Role: {role.capitalize()}")
    st.markdown("---")

    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()

if role == "employee":
    show_employee_dashboard()
elif role == "manager":
    show_manager_dashboard()
elif role == "admin":
    show_admin_dashboard()
else:
    st.error("Unknown role detected.")