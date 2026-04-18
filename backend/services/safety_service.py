import torch
import pickle
import re
import os
import numpy as np
import pandas as pd
from transformers import pipeline
from functools import lru_cache

# Optymalizacja wątków dla stabilności backendu
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'


class SafetyService:
    def __init__(self, model_path='../ml/local_models/safety_models.pkl'):
        """
        Zmergowany serwis bezpieczeństwa z dwoma modelami:
        - Brain (Diagnoza): TF-IDF + RandomForest na surowym tekście
        - Heart (Interpretacja): DistilBERT Emotions + emocje-based RandomForest
        """
        print("--- Initializing Safety Service (Brain + Heart) ---")

        # Try new combined model first, fallback to old one
        new_model_path = model_path
        old_model_path = '../ml/local_models/safety_model.pkl'
        
        if os.path.exists(new_model_path):
            with open(new_model_path, 'rb') as f:
                models_dict = pickle.load(f)
            self.tfidf_vectorizer = models_dict.get('tfidf_vectorizer')
            self.combined_model = models_dict.get('combined_model')
            self.emotion_model = models_dict.get('emotion_model')
            print("✓ Combined Model (TF-IDF + Emotions) loaded.")
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
        Zwraca prawdopodobieństwo ryzyka (0.0 - 1.0) z modelu połączonego.
        Połączony model używa: TF-IDF (słowa) + Emotions (sentymenty)
        """
        try:
            # Use combined model if available
            if self.combined_model and self.tfidf_vectorizer:
                return self._get_combined_risk(text)
            # Fallback to emotion model
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
        """Compute risk from combined model (TF-IDF + Emotions)."""
        try:
            # Get TF-IDF features
            tfidf_features = self.tfidf_vectorizer.transform([text]).toarray()
            
            # Get emotion features
            emotions_dict = self._get_cached_emotions(text)
            emotion_order = ['sadness', 'joy', 'love', 'anger', 'fear', 'surprise']
            emotion_features = [[emotions_dict.get(e, 0.0) for e in emotion_order]]
            
            # Combine features
            combined_features = np.hstack([tfidf_features, emotion_features])
            
            # Predict
            risk_score = self.combined_model.predict_proba(combined_features)[0][1]
            return round(float(risk_score), 4)
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
            # Combined model risk
            if self.combined_model and self.tfidf_vectorizer:
                detailed["combined_risk"] = self._get_combined_risk(text)
                
                # Get individual contributions
                tfidf_features = self.tfidf_vectorizer.transform([text]).toarray()
                emotions_dict = self._get_cached_emotions(text)
                
                # Store for feature importance analysis
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