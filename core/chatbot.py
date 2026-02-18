import streamlit as st
from groq import Groq
import os


class WellnessChatbot:

    def __init__(self):
        try:
            self.client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        except Exception:
            self.client = None

    def get_response(self, user_message, stress_score, history=None):

        if not self.client:
            return "AI configuration error. Please check GROQ_API_KEY."

        # 🔒 Limit memory to last 6 messages only
        if history:
            history = history[-6:]
        else:
            history = []

        # 🧠 Emotion-aware system prompt
        system_prompt = f"""
You are StressGuard AI, a professional emotional wellness assistant.

User stress score: {stress_score}/100.

Tone rules:
0-40 → calm, positive.
41-70 → structured, helpful guidance.
71-100 → grounding, step-by-step emotional support.

Be concise.
Avoid repeating previous responses.
Keep response under 200 words.
"""

        messages = [{"role": "system", "content": system_prompt}]

        # Add memory safely
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["message"]
            })

        # Add new user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        try:
            completion = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.7,
                max_tokens=250,   # 🔥 critical for stability
                top_p=0.9
            )

            return completion.choices[0].message.content

        except Exception:
            # 🛡 Safe fallback
            return "I'm having a small technical issue right now. Please try again in a moment."