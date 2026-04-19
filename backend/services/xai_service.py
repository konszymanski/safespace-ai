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
                "sadness": ["depressed mood", "hopelessness"],
                "fear": ["anxiety", "panic"],
                "anger": ["irritability", "hostility"],
            }
            for emotion, score in emotions.items():
                if score > 0.3 and emotion in risk_emotion_map:
                    risk_indicators.extend(risk_emotion_map[emotion])

            return {
                "emotions": emotions,
                "dominant_emotion": max(emotions.items(), key=lambda x: x[1])[0] if emotions else None,
                "risk_indicators": risk_indicators,
            }
        except Exception as e:
            print(f"Emotion interpretation error: {e}")
            return {"emotions": {}, "dominant_emotion": None, "risk_indicators": []}

    def get_diagnosis_interpretation(self, text: str):
        try:
            if not self.safety_service.tfidf_vectorizer or not self.safety_service.combined_model:
                return {"error": "Combined model not available", "keywords": []}

            tfidf_features = self.safety_service.tfidf_vectorizer.transform([text]).toarray()[0]
            emotions = self.safety_service._get_cached_emotions(text)
            emotion_order = ['sadness', 'joy', 'love', 'anger', 'fear', 'surprise']
            emotion_features = [emotions.get(e, 0.0) for e in emotion_order]

            combined_features = np.hstack([tfidf_features.reshape(1, -1), np.array(emotion_features).reshape(1, -1)])
            prediction_proba = self.safety_service.combined_model.predict_proba(combined_features)[0]
            risk_prob = float(prediction_proba[1])

            feature_names = self.safety_service.tfidf_vectorizer.get_feature_names_out()
            top_indices = (-tfidf_features).argsort()[:10]
            top_keywords = [
                {"word": feature_names[i], "tfidf_score": round(float(tfidf_features[i]), 4)}
                for i in top_indices if tfidf_features[i] > 0
            ]

            return {
                "diagnosis": "risky" if risk_prob > 0.5 else "safe",
                "risk_probability": round(risk_prob, 4),
                "top_keywords": top_keywords,
                "emotions": emotions,
            }
        except Exception as e:
            print(f"Diagnosis interpretation error: {e}")
            return {"error": str(e), "keywords": []}

    def get_explanations(self, text: str):
        """Word-level impact analysis. Reuses cached emotions to avoid re-running DistilBERT per word."""
        words = text.split()
        if not words or not self.safety_service.tfidf_vectorizer or not self.safety_service.combined_model:
            return []

        try:
            emotions = self.safety_service._get_cached_emotions(text)
            emotion_order = ['sadness', 'joy', 'love', 'anger', 'fear', 'surprise']
            emotion_features = np.array([[emotions.get(e, 0.0) for e in emotion_order]])

            tfidf_base = self.safety_service.tfidf_vectorizer.transform([text]).toarray()
            base_risk = float(self.safety_service.combined_model.predict_proba(
                np.hstack([tfidf_base, emotion_features])
            )[0][1])
        except Exception:
            return []

        explanations = []
        for i in range(len(words)):
            reduced_text = " ".join(words[:i] + words[i + 1:])
            try:
                tfidf_reduced = self.safety_service.tfidf_vectorizer.transform([reduced_text]).toarray()
                new_risk = float(self.safety_service.combined_model.predict_proba(
                    np.hstack([tfidf_reduced, emotion_features])
                )[0][1])
                impact = base_risk - new_risk
                explanations.append({"word": words[i], "impact": round(float(impact), 4)})
            except Exception:
                continue

        return sorted(explanations, key=lambda x: x["impact"], reverse=True)

    def get_full_analysis(self, text: str):
        all_sentences = self.get_sentence_risks(text)
        top_3_sentences = all_sentences[:3]

        results = []
        for sent in top_3_sentences:
            sentence_text = sent["text"]
            word_explanations = self.get_explanations(sentence_text)
            dangerous_words = [w for w in word_explanations if w["impact"] > 0.01]

            results.append({
                "sentence_id": sent["id"],
                "sentence_text": sentence_text,
                "sentence_risk": sent["risk_factor"],
                "top_dangerous_words": dangerous_words[:3],
            })

        return {
            "overall_text": text,
            "diagnosis": self.get_diagnosis_interpretation(text),
            "emotions": self.get_emotions_interpretation(text),
            "top_risk_analysis": results,
        }
