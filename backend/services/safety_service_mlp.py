import torch
import torch.nn as nn
import pickle
import re
import os
import numpy as np
from transformers import pipeline
from functools import lru_cache

class SafetyMLP(nn.Module):
    def __init__(self, input_size):
        super(SafetyMLP, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_size, 512),
            nn.GELU(),
            nn.BatchNorm1d(512),
            nn.Dropout(0.15),

            nn.Linear(512, 128),
            nn.GELU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.15),

            nn.Linear(128, 1),
            nn.Sigmoid()
        )
    def forward(self, x):
        return self.layers(x)

    def predict_proba(self, x):
        self.eval()
        with torch.no_grad():
            if isinstance(x, np.ndarray):
                x_tensor = torch.from_numpy(x).float()
            else:
                x_tensor = x.float()

            if x_tensor.ndim == 1:
                x_tensor = x_tensor.unsqueeze(0)

            prob = self.forward(x_tensor)
            prob_0 = 1 - prob
            return torch.cat([prob_0, prob], dim=1).cpu().numpy()


class SafetyServiceMLP:
    def __init__(self):
        print("--- Initializing Neural Safety Service (MLP + GoEmotions) ---")

        base_path = os.path.join(os.path.dirname(__file__), '..', 'ml', 'local_models')
        pkl_path = os.path.join(base_path, 'safety_mlp_new_bert.pkl')
        pth_path = os.path.join(base_path, 'safety_mlp_new_bert.pth')

        try:
            if not os.path.exists(pkl_path):
                raise FileNotFoundError(f"Brak pliku .pkl w: {pkl_path}")

            with open(pkl_path, 'rb') as f:
                config_dict = pickle.load(f)

            self.emotion_cols = config_dict.get('emotion_cols')
            if not self.emotion_cols:
                raise ValueError("Plik .pkl nie zawiera klucza 'emotion_cols'!")

            if not os.path.exists(pth_path):
                raise FileNotFoundError(f"Brak wag .pth w: {pth_path}")

            self.model = SafetyMLP(input_size=len(self.emotion_cols))
            self.model.load_state_dict(torch.load(pth_path, map_location=torch.device('cpu')))
            self.model.eval()

            self.emotion_classifier = pipeline(
                "text-classification",
                model="monologg/bert-base-cased-goemotions-original",
                top_k=None,
                device=-1
            )

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

            print(f"✓ Neural Engine Ready. Features: {len(self.emotion_cols)}")

        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            raise

    @lru_cache(maxsize=128)
    def _get_cached_emotions(self, text):
        res = self.emotion_classifier(text[:512])[0]
        return {item['label']: item['score'] for item in res}

    def _prepare_vector(self, text):
        ems = self._get_cached_emotions(text)
        return np.array([ems.get(col, 0.0) for col in self.emotion_cols]).reshape(1, -1)

    def get_risk_score(self, text):
        try:
            vector = self._prepare_vector(text)
            probs = self.model.predict_proba(vector)
            return round(float(probs[0][1]), 4)
        except Exception as e:
            print(f"❌ Error in get_risk_score: {e}")
            return 0.0

    def analyze(self, text):
        risk_score = self.get_risk_score(text)
        text_lower = text.lower()

        detected_symptoms = [
            s for s, keywords in self.phq9_map.items()
            if any(re.search(rf'\b{re.escape(word)}\b', text_lower) for word in keywords)
        ]

        if "suicidal_ideation" in detected_symptoms:
            risk_score = max(risk_score, 0.85)

        return {
            "risk_score": risk_score,
            "is_safe": risk_score < 0.5,
            "status": "Red Flag" if risk_score >= 0.5 else "Stable",
            "clinical_metrics": {
                "symptoms": detected_symptoms,
                "phq9_est": min(len(detected_symptoms) * 3, 27)
            }
        }