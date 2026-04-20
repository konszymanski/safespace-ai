import re
import numpy as np

class XAIService:
    def __init__(self, safety_service):
        self.safety_service = safety_service

    def get_sentence_risks(self, text: str):
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())

        sentence_analysis = []

        for idx, sentence in enumerate(sentences):
            if not sentence.strip():
                continue

            try:
                risk_score = self.safety_service.get_risk_score(sentence)
                sentence_analysis.append({
                    "id": idx,
                    "text": sentence,
                    "risk_factor": round(float(risk_score), 4),
                })
            except Exception as e:
                print(f"XAI Error at sentence {idx}: {e}")
                continue

        return sorted(sentence_analysis, key=lambda x: x["risk_factor"], reverse=True)

    def get_most_dangerous_sentence(self, text: str):
        analysis = self.get_sentence_risks(text)
        return analysis[0] if analysis else None

    def get_emotions_interpretation(self, text: str):
        try:
            emotions = self.safety_service._get_cached_emotions(text)
            risk_indicators = []
            risk_emotion_map = {
                "sadness": ["depressed mood"],
                "grief": ["intense sorrow", "loss"],
                "remorse": ["pathological guilt"],
                "disappointment": ["hopelessness"],
                "fear": ["anxiety", "acute fear"],
                "nervousness": ["tension", "restlessness"],
                "confusion": ["disorientation", "mental fog"],
                "anger": ["hostility"],
                "annoyance": ["irritability"],
                "disgust": ["self-loathing (if self-directed)"],
                "neutral": ["emotional numbness"]
            }
            for emotion, score in emotions.items():
                if score > 0.3 and emotion in risk_emotion_map:
                    risk_indicators.extend(risk_emotion_map[emotion])

            return {
                "emotions": emotions,
                "dominant_emotion": max(emotions.items(), key=lambda x: x[1])[0] if emotions else None,
                "risk_indicators": list(set(risk_indicators)),
            }
        except Exception as e:
            print(f"Emotion interpretation error: {e}")
            return {"emotions": {}, "dominant_emotion": None, "risk_indicators": []}

    def get_explanations(self, text: str):
        words = text.split()
        if not words:
            return []

        try:
            base_risk = self.safety_service.get_risk_score(text)
        except Exception:
            return []

        explanations = []
        for i in range(len(words)):
            reduced_text = " ".join(words[:i] + words[i + 1:])
            try:
                new_risk = self.safety_service.get_risk_score(reduced_text)
                impact = base_risk - new_risk
                explanations.append({
                    "word": words[i],
                    "impact": round(float(impact), 4)
                })
            except Exception:
                continue

        return sorted(explanations, key=lambda x: x["impact"], reverse=True)

    def get_full_analysis(self, text: str):
        """
        Zaktualizowana wersja bez diagnosis_interpretation.
        Integruje wyniki MLP, emocje i analizę zdań.
        """
        all_sentences = self.get_sentence_risks(text)
        top_3_sentences = all_sentences[:3]

        emotion_data = self.get_emotions_interpretation(text)

        overall_risk = self.safety_service.get_risk_score(text)

        sentence_results = []
        for sent in top_3_sentences:
            sentence_text = sent["text"]
            word_explanations = self.get_explanations(sentence_text)
            dangerous_words = [w for w in word_explanations if w["impact"] > 0.005]

            sentence_results.append({
                "sentence_id": sent["id"],
                "sentence_text": sentence_text,
                "sentence_risk": sent["risk_factor"],
                "top_dangerous_words": dangerous_words[:3],
            })

        return {
            "overall_text": text,
            "overall_risk_score": overall_risk,
            "status": "🚨 DANGER" if overall_risk >= 0.5 else "✅ SAFE",
            "emotions_analysis": emotion_data,
            "top_sentence_analysis": sentence_results,
        }
