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
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
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
            self.tfidf = joblib.load(os.path.join(base_path, 'tfidf_vectorizer.pkl'))
            self.scaler = joblib.load(os.path.join(base_path, 'scaler.pkl'))

            input_dim = len(self.tfidf.get_feature_names_out()) + 6
            self.model = SafetyMLP(input_dim)
            self.model.load_state_dict(torch.load(os.path.join(base_path, 'safety_mlp.pth')))
            self.model.eval()

            self.emotion_clf = pipeline("text-classification",
                                        model="bhadresh-savani/distilbert-base-uncased-emotion",
                                        top_k=None, device=-1)

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
            tfidf_feat = self.tfidf.transform([self._clean_text(text)]).toarray()

            ems = self._get_emotions(text)
            em_order = ['sadness', 'joy', 'love', 'anger', 'fear', 'surprise']
            em_feat = np.array([ems.get(e, 0.0) for e in em_order]).reshape(1, -1)

            combined = np.hstack([tfidf_feat, em_feat])
            scaled = self.scaler.transform(combined)

            with torch.no_grad():
                tensor_input = torch.FloatTensor(scaled)
                score = self.model(tensor_input).item()

            return round(float(score), 4)
        except Exception as e:
            print(f"Prediction error: {e}")
            return 0.0

    def analyze(self, text):
        score = self.get_risk_score(text)
        return {
            "risk_score": score,
            "is_safe": score < 0.5,
            "status": "Red Flag" if score >= 0.5 else "Stable"
        }