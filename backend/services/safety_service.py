import torch
import pickle
import re
import os
import pandas as pd
from transformers import pipeline
from functools import lru_cache

# Optymalizacja wątków dla stabilności backendu
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'


class SafetyService:
    def __init__(self, model_path='../../ml/local_models/safety_model.pkl'):
        """
        Zmergowany serwis bezpieczeństwa.
        Łączy klasyfikator emocji (Transformer) z modelem ryzyka (Random Forest).
        """
        print("--- Initializing New Safety Service ---")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model pkl nie znaleziony w: {model_path}")

        with open(model_path, 'rb') as f:
            self.safety_model = pickle.load(f)
        print("✓ Safety Model (RandomForest) loaded.")

        self.emotion_classifier = pipeline(
            "text-classification",
            model="bhadresh-savani/distilbert-base-uncased-emotion",
            top_k=None,
            device=-1
        )
        print("✓ Emotion Transformer loaded.")

        self.phq9_map = {
            "anhedonia": ["interest", "pleasure", "hobbies", "bored", "nothing feels good", "don't care"],
            "depressed_mood": ["sad", "hopeless", "depressed", "miserable", "down", "crying", "blue"],
            "sleep_issues": ["sleep", "insomnia", "waking up", "oversleeping", "can't sleep", "restless"],
            "energy_loss": ["tired", "no energy", "exhausted", "fatigue", "drained", "heavy"],
            "appetite_issues": ["appetite", "eating", "hungry", "food", "weight", "binge", "starving"],
            "low_self_esteem": ["failure", "let down", "useless", "worthless", "hate myself", "disappointed"],
            "concentration": ["focus", "concentrating", "distracted", "brain fog", "can't think", "reading"],
            "psychomotor": ["slow", "moving slow", "jittery", "pacing", "restless", "fidgeting"],
            "suicidal_ideation": ["die", "suicide", "end it", "kill myself", "hurt myself", "better off dead"]
        }
        print("--- Safety Service Ready ---")

    def get_risk_score(self, text: str) -> float:
        """
        Kluczowa metoda dla XAIService.
        Zwraca prawdopodobieństwo ryzyka (0.0 - 1.0).
        """
        try:
            features = self._get_emotions_vector(text)
            # predict_proba zwraca [[prawd_0, prawd_1]] -> bierzemy prawd_1 (ryzyko)
            risk_score = self.safety_model.predict_proba(features)[0][1]
            return round(float(risk_score), 4)
        except Exception as e:
            print(f"Error in get_risk_score: {e}")
            return 0.0

    def analyze(self, text: str):
        """Pełna analiza dla backendu: ryzyko + emocje + PHQ-9."""
        risk_score = self.get_risk_score(text)

        detected_symptoms = [
            s for s, keywords in self.phq9_map.items()
            if any(re.search(rf'\b{re.escape(word)}\b', text.lower()) for word in keywords)
        ]

        return {
            "risk_score": risk_score,
            "is_safe": risk_score < 0.5,  # Próg bezpieczeństwa
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