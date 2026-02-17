import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class WellnessChatbot:
    def __init__(self):
        # ✅ Use a confirmed working model
        self.model = genai.GenerativeModel("models/gemini-flash-latest")

    def get_response(self, user_message: str) -> str:
        prompt = f"""
You are a calm, empathetic employee wellness assistant.

Rules:
- Listen carefully
- Validate emotions
- Give gentle, non-medical advice
- NEVER judge
- NEVER diagnose

Employee message:
"{user_message}"
"""
        response = self.model.generate_content(prompt)
        return response.text

