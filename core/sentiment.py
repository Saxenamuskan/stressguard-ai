from textblob import TextBlob

class StressAnalyzer:
    def analyze_text(self, text):
        polarity = TextBlob(text).sentiment.polarity

        # Convert polarity (-1 to 1) to stress score (0 to 100)
        stress_score = int((1 - polarity) * 50)

        if stress_score < 0:
            stress_score = 0
        if stress_score > 100:
            stress_score = 100

        return stress_score