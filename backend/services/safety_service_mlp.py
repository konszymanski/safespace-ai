import torch
import torch.nn as nn
import joblib
import re
import os
import numpy as np
from transformers import pipeline
from functools import lru_cache


class SafetyMLP(nn.Module):
    def __init__(self, input_size):
        super(SafetyMLP, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.4),

            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.layers(x)


class SafetyServiceMLP:
    def __init__(self):
        print("--- Initializing Neural Safety Service (MLP + DistilBERT) ---")

        # Ścieżki dynamiczne
        base_path = os.path.join(os.path.dirname(__file__), '..', 'ml', 'local_models')

        try:
            self.tfidf_vectorizer = joblib.load(os.path.join(base_path, 'tfidf_vectorizer.pkl'))
            self.scaler = joblib.load(os.path.join(base_path, 'scaler.pkl'))

            input_dim = len(self.tfidf_vectorizer.get_feature_names_out()) + 6
            self.combined_model = SafetyMLP(input_dim)
            self.combined_model.load_state_dict(torch.load(os.path.join(base_path, 'safety_mlp.pth')))
            self.combined_model.eval()

            self.emotion_clf = pipeline("text-classification",
                                        model="bhadresh-savani/distilbert-base-uncased-emotion",
                                        top_k=None, device=-1)

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

            print("✓ Neural Engine & Transformer loaded successfully.")
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            raise

    def _clean_text(self, text):
        text = text.lower()
        return re.sub(r'[^\w\s]', '', text).strip()

    @lru_cache(maxsize=128)
    def _get_emotions(self, text):
        res = self.emotion_clf(text[:512])[0]
        return {item['label']: item['score'] for item in res}

    def get_risk_score(self, text):
        try:
            cleaned = self._clean_text(text)
            tfidf_feat = self.tfidf_vectorizer.transform([cleaned]).toarray()

            ems = self._get_emotions(text)
            em_order = ['sadness', 'joy', 'love', 'anger', 'fear', 'surprise']
            em_feat = np.array([ems.get(e, 0.0) for e in em_order]).reshape(1, -1)

            combined = np.hstack([tfidf_feat, em_feat])
            scaled = self.scaler.transform(combined)

            with torch.no_grad():
                tensor_input = torch.FloatTensor(scaled)
                output = self.combined_model(tensor_input)
                score = output.item()

            return round(float(score), 4)

        except Exception as e:
            print(f"❌ ERROR in get_risk_score: {e}")
            return 0.0

    def analyze(self, text):
        risk_score = self.get_risk_score(text)

        detected_symptoms = [
            s for s, keywords in self.phq9_map.items()
            if any(re.search(rf'\b{re.escape(word)}\b', text.lower()) for word in keywords)
        ]

        return {
            "risk_score": risk_score,
            "is_safe": risk_score < 0.5,
            "status": "Red Flag" if risk_score >= 0.5 else "Stable",
            "clinical_metrics": {
                "symptoms": detected_symptoms,
                "phq9_est": min(len(detected_symptoms) * 3, 27)
            }
        }