from transformers import pipeline

class StressAnalyzer:
    def __init__(self):
        self.emotion_model = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            top_k=None
        )

    def analyze_text(self, text):
        emotions = self.emotion_model(text)[0]

        # Emotion → Stress weight mapping
        stress_weights = {
            "fear": 90,
            "anger": 85,
            "sadness": 70,
            "disgust": 60,
            "surprise": 30,
            "joy": -40
        }

        stress_score = 0
        for emotion in emotions:
            label = emotion["label"]
            score = emotion["score"]
            stress_score += score * stress_weights.get(label, 0)

        # Clamp score between 0–100
        stress_score = max(0, min(100, int(stress_score)))

        return stress_score
