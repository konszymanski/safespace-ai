import pickle
import re
import os
import torch
import numpy as np
import pandas as pd
from transformers import pipeline
from functools import lru_cache


class SafetyService:
    def __init__(self):
        base_path = os.path.join(os.path.dirname(__file__), '..', 'ml', 'local_models')
        model_path = os.path.join(base_path, 'safety_model_tuned_bayes.pkl')

        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                models_dict = pickle.load(f)

            self.model = models_dict.get('model')
            self.emotion_cols = models_dict.get('emotion_cols')
            metadata = models_dict.get('metadata', {})

            print(f"✓ Model loaded. Features: {metadata.get('feature_count')} (BERT Emotions)")
        else:
            raise FileNotFoundError(f"Model pkl nie znaleziony w: {model_path}")


        self.emotion_classifier = pipeline(
            "text-classification",
            model="monologg/bert-base-cased-goemotions-original",
            top_k=None,
            device=-1
        )
        print("[OK] BERT GoEmotions Transformer loaded.")

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

    @lru_cache(maxsize=128)
    def _get_cached_emotions(self, text: str):
        """Pobiera pełny słownik 28 emocji z modelu BERT."""
        results = self.emotion_classifier(text[:512])
        return {res['label']: res['score'] for res in results[0]}

    def _prepare_feature_vector(self, text: str):
        """Przygotowuje DataFrame z 28 cechami w poprawnej kolejności."""
        emotions_dict = self._get_cached_emotions(text)
        vector = [[emotions_dict.get(col, 0.0) for col in self.emotion_cols]]
        return pd.DataFrame(vector, columns=self.emotion_cols)

    def get_risk_score(self, text: str) -> float:
        """Zwraca prawdopodobieństwo ryzyka z modelu MLP/NN."""
        try:
            features = self._prepare_feature_vector(text)

            probabilities = self.model.predict_proba(features)

            risk_score = probabilities[0][1]

            return round(float(risk_score), 4)

        except Exception as e:
            print(f"Error in get_risk_score (sklearn): {e}")
            return 0.0

    def analyze(self, text: str):
        """Pełna analiza: ryzyko modelowe + reguły PHQ-9."""
        risk_score = self.get_risk_score(text)

        detected_symptoms = [
            s for s, keywords in self.phq9_map.items()
            if any(re.search(rf'\b{re.escape(word)}\b', text.lower()) for word in keywords)
        ]

        #if "suicidal_ideation" in detected_symptoms:
        #    risk_score = max(risk_score, 0.75)
        return {
            "risk_score": risk_score,
            "is_safe": risk_score < 0.5,
            "clinical_metrics": {
                "symptoms": detected_symptoms,
                "phq9_est": min(len(detected_symptoms) * 3, 27)
            }

        }