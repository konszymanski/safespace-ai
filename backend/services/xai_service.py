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
                detailed = self.safety_service.get_risk_scores_detailed(sentence)

                sentence_analysis.append({
                    "id": idx,
                    "text": sentence,
                    "risk_factor": round(float(risk_score), 4),
                    "combined_risk": detailed.get("combined_risk", 0.0)
                })
            except Exception as e:
                print(f"XAI Error at sentence {idx}: {e}")
                continue

        return sorted(sentence_analysis, key=lambda x: x["risk_factor"], reverse=True)

    def get_most_dangerous_sentence(self, text: str):
        analysis = self.get_sentence_risks(text)
        return analysis[0] if analysis else None

    def get_emotions_interpretation(self, text: str):
        """
        Heart - Interpretacja: Pokazuje jakie emocje odczuwa użytkownik
        i dlaczego mogą wskazywać na kryzys/depresję.
        """
        try:
            emotions = self.safety_service._get_cached_emotions(text)
            
            emotion_interpretation = {
                "emotions": emotions,
                "dominant_emotion": max(emotions.items(), key=lambda x: x[1])[0] if emotions else None,
                "risk_indicators": []
            }
            
            # Map emotions to risk indicators
            risk_keywords = {
                "sadness": ["depressed mood", "hopelessness"],
                "fear": ["anxiety", "panic", "worry"],
                "anger": ["irritability", "hostility"],
                "surprise": [],
                "joy": ["positive sign"],
                "love": ["connection", "support"]
            }
            
            for emotion, score in emotions.items():
                if score > 0.3:  # Significant emotion
                    indicators = risk_keywords.get(emotion, [])
                    if emotion in ["sadness", "fear", "anger"]:
                        emotion_interpretation["risk_indicators"].extend(indicators)
            
            return emotion_interpretation
        except Exception as e:
            print(f"Emotion interpretation error: {e}")
            return {"emotions": {}, "dominant_emotion": None, "risk_indicators": []}

    def get_diagnosis_interpretation(self, text: str):
        """
        Brain - Diagnoza: Pokazuje jakie słowa/cechy TF-IDF i emocje wpływają na diagnozę
        (depresja/kryzys vs normalny stan).
        """
        try:
            if not self.safety_service.tfidf_vectorizer or not self.safety_service.combined_model:
                return {"error": "Combined model not available", "keywords": []}
            
            # Transform text with TF-IDF
            tfidf_features = self.safety_service.tfidf_vectorizer.transform([text]).toarray()[0]
            
            # Get emotions
            emotions = self.safety_service._get_cached_emotions(text)
            emotion_order = ['sadness', 'joy', 'love', 'anger', 'fear', 'surprise']
            emotion_features = [emotions.get(e, 0.0) for e in emotion_order]
            
            # Combine features
            combined_features = np.hstack([tfidf_features.reshape(1, -1), np.array(emotion_features).reshape(1, -1)])
            
            # Get model prediction
            prediction_proba = self.safety_service.combined_model.predict_proba(combined_features)[0]
            
            # Get top TF-IDF keywords
            feature_names = self.safety_service.tfidf_vectorizer.get_feature_names_out()
            top_indices = (-tfidf_features).argsort()[:10]
            top_keywords = [
                {
                    "word": feature_names[i],
                    "tfidf_score": round(float(tfidf_features[i]), 4)
                }
                for i in top_indices if tfidf_features[i] > 0
            ]
            
            return {
                "diagnosis": "risky" if prediction_proba[1] > 0.5 else "safe",
                "confidence": round(float(max(prediction_proba)), 4),
                "risk_probability": round(float(prediction_proba[1]), 4),
                "top_keywords": top_keywords,
                "emotions": emotions
            }
        except Exception as e:
            print(f"Diagnosis interpretation error: {e}")
            return {"error": str(e), "keywords": []}

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
            except:
                continue

        return sorted(explanations, key=lambda x: x["impact"], reverse=True)

    def get_full_analysis(self, text: str):
        all_sentences = self.get_sentence_risks(text)

        top_3_sentences = all_sentences[:3]

        results = []

        for sent in top_3_sentences:
            sentence_text = sent["text"]

            word_explanations = self.get_explanations(sentence_text)

            dangerous_words = [
                w for w in word_explanations if w["impact"] > 0.01
            ]

            dangerous_words.sort(key=lambda x: x["impact"], reverse=True)

            results.append({
                "sentence_id": sent["id"],
                "sentence_text": sentence_text,
                "sentence_risk": sent["risk_factor"],
                "combined_risk": sent.get("combined_risk", 0.0),  # Combined model diagnosis
                "top_dangerous_words": dangerous_words[:3]
            })

        return {
            "overall_text": text,
            "diagnosis": self.get_diagnosis_interpretation(text),  # Brain analysis
            "emotions": self.get_emotions_interpretation(text),    # Heart analysis
            "top_risk_analysis": results
        }