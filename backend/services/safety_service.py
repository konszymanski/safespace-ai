import pickle
import re
import os
import numpy as np
import pandas as pd
from transformers import pipeline
from functools import lru_cache

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

# Resolve artifacts relative to this package (…/backend/), not process cwd (uvicorn / Docker WORKDIR).
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_MODELS_PKL = os.path.join(_BACKEND_ROOT, "ml", "local_models", "safety_models.pkl")
_DEFAULT_LEGACY_PKL = os.path.join(_BACKEND_ROOT, "ml", "local_models", "safety_model.pkl")


class SafetyService:
    def __init__(self, model_path: str | None = None):
        new_model_path = model_path or _DEFAULT_MODELS_PKL
        old_model_path = _DEFAULT_LEGACY_PKL
        
        if os.path.exists(new_model_path):
            with open(new_model_path, 'rb') as f:
                models_dict = pickle.load(f)
            self.tfidf_vectorizer = models_dict.get('tfidf_vectorizer')
            self.combined_model = models_dict.get('combined_model')
            self.emotion_model = models_dict.get('emotion_model')
            print("✓ Feature metadata:", models_dict.get('feature_count', {}))
        elif os.path.exists(old_model_path):
            with open(old_model_path, 'rb') as f:
                self.emotion_model = pickle.load(f)
            self.tfidf_vectorizer = None
            self.combined_model = None
            print("✓ Emotion Model (Legacy mode) loaded.")
        else:
            raise FileNotFoundError(f"Model pkl nie znaleziony w: {new_model_path} ani {old_model_path}")

        self.emotion_classifier = pipeline(
            "text-classification",
            model="bhadresh-savani/distilbert-base-uncased-emotion",
            top_k=None,
            device=-1
        )
        print("[OK] Emotion Transformer loaded.")

        self.phq9_map = {
            "anhedonia": ["interest", "pleasure", "hobbies", "bored", "nothing feels good", "don't care"],
            "depressed_mood": ["sad", "hopeless", "depressed", "miserable", "down", "crying", "blue"],
            "sleep_issues": ["sleep", "insomnia", "waking up", "oversleeping", "can't sleep", "restless"],
            "energy_loss": ["tired", "no energy", "exhausted", "fatigue", "drained", "heavy"],
            "appetite_issues": ["appetite", "eating", "hungry", "food", "weight", "binge", "starving"],
            "low_self_esteem": ["failure", "let down", "useless", "worthless", "hate myself", "disappointed"],
            "concentration": ["focus", "concentrating", "distracted", "brain fog", "can't think", "reading"],
            "psychomotor": ["slow", "moving slow", "jittery", "pacing", "restless", "fidgeting"],
            "suicidal_ideation": ["die", "suicide", "end it", "kill myself", "hurt myself", "better off dead", 
                                 "want to die", "no reason to live", "end my life", "final goodbye", 
                                 "never wake up", "fall asleep forever", "sleep forever", "disappear",
                                 "not worth living", "wish i was dead", "want to end it", "end it tonight",
                                 "goodbye forever", "last goodbye", "final note", "ending it",
                                 "can't take this anymore", "no point in living", "better off without me",
                                 "world better without me", "family better without me", "everyone better off",
                                 "pills to sleep forever", "find some pills", "sleep forever",
                                 "tired of existing", "ghost watching", "fade away", "nothing numb",
                                 "lock the door", "write notes", "ending it tonight"]
        }
        print("--- Safety Service Ready ---")

    def get_risk_score(self, text: str) -> float:
        """
        Kluczowa metoda dla XAIService.
        Zwraca prawdopodobieństwo ryzyka (0.0 - 1.0) z modelu połączonego.
        Połączony model używa: TF-IDF (słowa) + Emotions (sentymenty) + RandomForest
        """
        try:
            if self.combined_model and self.tfidf_vectorizer:
                return self._get_combined_risk(text)
            elif self.emotion_model:
                emotions_vector = self._get_emotions_vector(text)
                risk_score = self.emotion_model.predict_proba(emotions_vector)[0][1]
                return round(float(risk_score), 4)
            else:
                return 0.0
        except Exception as e:
            print(f"Error in get_risk_score: {e}")
            return 0.0

    def _get_combined_risk(self, text: str) -> float:
        """Compute risk from combined model (TF-IDF + Emotions + RandomForest) with rule-based boosts."""
        try:
            tfidf_features = self.tfidf_vectorizer.transform([text]).toarray()
            emotions_dict = self._get_cached_emotions(text)
            emotion_order = ['sadness', 'joy', 'love', 'anger', 'fear', 'surprise']
            emotion_features = [[emotions_dict.get(e, 0.0) for e in emotion_order]]
            combined_features = np.hstack([tfidf_features, emotion_features])
            base_risk_score = self.combined_model.predict_proba(combined_features)[0][1]

            text_lower = text.lower()
            sadness_score = emotions_dict.get('sadness', 0.0)

            frustration_contexts = [
                "internet", "wifi", "connection", "laptop", "computer", "pc",
                "video game", "game", "boss", "level", "match", "traffic",
                "work project", "deadline", "presentation", "exam", "test"
            ]
            frustration_phrases = ["killing me", "is killing", "it's killing", "will kill me"]
            in_frustration_context = (
                any(ctx in text_lower for ctx in frustration_contexts) and
                any(phrase in text_lower for phrase in frustration_phrases)
            )
            if in_frustration_context:
                base_risk_score = min(base_risk_score, 0.40)

            depression_keywords = [
                "no energy", "no motivation", "can't get out of bed", "hard to get up",
                "lost interest", "lost all interest", "don't enjoy", "feel empty",
                "feel numb", "feel nothing", "feel hollow", "going through motions",
                "gray and heavy", "feels gray", "heavy lately", "walking through mud",
                "feels heavy", "everything feels", "gray inside",
                "hard to get out", "find it hard", "hard to even",
                "feel invisible", "feel like a burden", "worthless", "hopeless",
                "can't stop crying", "cry myself", "no point", "what's the point",
                "nobody cares", "all alone", "completely alone", "isolat",
                "don't see the point", "feel disgusted with myself",
                "hate myself", "can't stop blaming", "letting everyone down"
            ]
            has_depression_keywords = any(kw in text_lower for kw in depression_keywords)
            depression_boost = 0.0
            if has_depression_keywords and sadness_score > 0.5:
                depression_boost = 0.25
            elif has_depression_keywords:
                depression_boost = 0.20

            suicidal_keywords = [
                "kill myself", "end it", "suicide", "want to die", "no reason to live",
                "end my life", "final goodbye", "never wake up", "fall asleep forever",
                "sleep forever", "not worth living", "wish i was dead",
                "want to end it", "end it tonight", "goodbye forever", "last goodbye",
                "final note", "ending it", "no point in living",
                "better off without me", "world better without me", "family better without me",
                "everyone better off", "pills to sleep forever", "find some pills",
                "tired of existing", "lock the door", "write notes", "ending it tonight",
                "no reason to live anymore", "everything is dark",
                "fall asleep and never wake up", "never wake up again", "planning to end my life",
                "written my letters", "ready to go", "final goodbye to everyone",
                "better off dead", "i am better off dead"
            ]
            suicidal_boost = 0.0
            has_suicidal_keywords = any(keyword in text_lower for keyword in suicidal_keywords)
            if has_suicidal_keywords:
                suicidal_boost = 0.4
            if has_suicidal_keywords and sadness_score > 0.7:
                suicidal_boost += 0.2

            final_risk = min(base_risk_score + depression_boost + suicidal_boost, 0.95)
            return round(float(final_risk), 4)
        except Exception as e:
            print(f"Error in _get_combined_risk: {e}")
            return 0.0

    def get_risk_scores_detailed(self, text: str) -> dict:
        """
        Zwraca detailowe info o ryzyku i cechach które wpłynęły na decyzję.
        """
        detailed = {
            "combined_risk": 0.0,
            "tfidf_contribution": None,
            "emotion_contribution": None
        }
        
        try:
            if self.combined_model and self.tfidf_vectorizer:
                detailed["combined_risk"] = self._get_combined_risk(text)

                tfidf_features = self.tfidf_vectorizer.transform([text]).toarray()
                emotions_dict = self._get_cached_emotions(text)

                detailed["tfidf_contribution"] = {
                    "num_features": tfidf_features.shape[1],
                    "non_zero": int((tfidf_features > 0).sum())
                }
                detailed["emotion_contribution"] = emotions_dict
        except Exception as e:
            print(f"Error in get_risk_scores_detailed: {e}")
        
        return detailed

    def analyze(self, text: str):
        """Pełna analiza dla backendu: ryzyko + emocje + PHQ-9."""
        risk_score = self.get_risk_score(text)

        detected_symptoms = [
            s for s, keywords in self.phq9_map.items()
            if any(re.search(rf'\b{re.escape(word)}\b', text.lower()) for word in keywords)
        ]

        if "suicidal_ideation" in detected_symptoms:
            risk_score = max(risk_score, 0.75) 

        return {
            "risk_score": risk_score,
            "is_safe": risk_score < 0.5,
            "clinical_metrics": {
                "symptoms": detected_symptoms,
                "phq9_est": min(len(detected_symptoms) * 3, 27)
            }
        }

    @lru_cache(maxsize=128)
    def _get_cached_emotions(self, text: str):
        results = self.emotion_classifier(text[:512])
        return {res['label']: res['score'] for res in results[0]}

    def _get_emotions_vector(self, text: str):
        emotions_dict = self._get_cached_emotions(text)
        emotion_order = ['sadness', 'joy', 'love', 'anger', 'fear', 'surprise']
        return pd.DataFrame([{e: emotions_dict.get(e, 0.0) for e in emotion_order}])