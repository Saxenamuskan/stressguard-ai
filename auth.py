import streamlit as st
from core.database import login_user, register_user

def show_login():

    st.subheader("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = login_user(username, password)

        if user:
            st.session_state.logged_in = True
            st.session_state.user_id = user["id"]
            st.session_state.role = user["role"]
            st.success("Login Successful")
            st.rerun()
        else:
            st.error("Invalid credentials")


def show_register():
    st.subheader("📝 Register")

    username = st.text_input("New Username")
    password = st.text_input("New Password", type="password")
    role = st.selectbox("Role", ["employee", "manager", "admin"])

    if st.button("Register"):
        register_user(username, password, role)
        st.success("User Registered Successfully")