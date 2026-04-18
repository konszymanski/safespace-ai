import torch  # Silnik AI
import pickle  # Do wczytania zapisanego modelu RandomForest
import re  # Wyrażenia regularne do szukania konkretnych słów (PHQ-9)
import os  # Zarządzanie systemem operacyjnym
from transformers import pipeline  # Do wczytania modelu emocji
import pandas as pd  # Dodane dla DataFrame

# Ustawienia optymalizujące wydajność na procesorach wielordzeniowych
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK']='True'

class MentalHealthBrain:
    def __init__(self, model_path='local_models/safety_model.pkl'):
        # Inicjalizacja klasy - wczytywanie wszystkiego do RAM-u na starcie
        print("1/2 Loading Stable Safety Model...")
        if not os.path.exists(model_path):  # Sprawdzenie czy plik modelu w ogóle istnieje
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        with open(model_path, 'rb') as f:
            self.safety_model = pickle.load(f)  # Wczytanie wytrenowanego lasu losowego
        print("Safety Model ready!")

        print("2/2 Loading Emotion Classifier (Transformers)...")
        self.emotion_classifier = pipeline(
            "text-classification", 
            model="bhadresh-savani/distilbert-base-uncased-emotion", 
            top_k=None,  # Chcemy pełen zestaw emocji dla modelu bezpieczeństwa
            device=-1  # Wymuszamy CPU, żeby uniknąć konfliktów z GPU na backendzie
        )
        print("Brain is fully functional!")

        # Twoja mapa kliniczna (uproszczone PHQ-9) do szukania konkretnych objawów
        self.phq9_map = {
        # 1. Niewielkie zainteresowanie lub przyjemność (Anhedonia)
        "anhedonia": ["interest", "pleasure", "hobbies", "bored", "nothing feels good", "don't care"],
    
        # 2. Smutek, przygnębienie, beznadziejność
        "depressed_mood": ["sad", "hopeless", "depressed", "miserable", "down", "crying", "blue"],
    
        # 3. Kłopoty ze snem (bezsenność lub nadmierna senność)
        "sleep_issues": ["sleep", "insomnia", "waking up", "oversleeping", "can't sleep", "restless"],
    
        # 4. Zmęczenie lub brak energii
        "energy_loss": ["tired", "no energy", "exhausted", "fatigue", "drained", "heavy"],
    
        # 5. Brak apetytu lub przejadanie się
        "appetite_issues": ["appetite", "eating", "hungry", "food", "weight", "binge", "starving"],
    
        # 6. Poczucie niezadowolenia z siebie / bycie do niczego
        "low_self_esteem": ["failure", "let down", "useless", "worthless", "hate myself", "disappointed"],
    
        # 7. Problemy ze skupieniem (np. przy czytaniu/TV)
        "concentration": ["focus", "concentrating", "distracted", "brain fog", "can't think", "reading"],
    
        # 8. Spowolnienie lub pobudzenie (psychoruchowe)
        "psychomotor": ["slow", "moving slow", "jittery", "pacing", "restless", "fidgeting"],
    
        # 9. Myśli o śmierci lub zrobieniu sobie krzywdy
        "suicidal_ideation": ["die", "suicide", "end it", "kill myself", "hurt myself", "better off dead"]
}

    def _get_emotions(self, text):
        # Pomocnicza funkcja: zamienia tekst na słownik emocji
        results = self.emotion_classifier(text[:512])  # Analiza Transformers
        return {res['label']: res['score'] for res in results[0]}  # Konwersja na ładny słownik

    def analyze(self, text):
        # GŁÓWNA METODA - to ją wywołuje Backend
        emotions_dict = self._get_emotions(text)  # Krok 1: Jakie to emocje?
        
        # Krok 2: Przygotowanie danych dla modelu bezpieczeństwa (musi być ta sama kolejność co w treningu!)
        emotion_order = ['sadness', 'joy', 'love', 'anger', 'fear', 'surprise']
        feature_df = pd.DataFrame(
            [{e: emotions_dict.get(e, 0.0) for e in emotion_order}]
        )
        
        # Krok 3: Ile procent ryzyka widzi model (0.0 - 1.0)
        risk_score = float(self.safety_model.predict_proba(feature_df)[0][1])
        
        # Krok 4: Szukanie klinicznych słów kluczowych
        detected_symptoms = [s for s, keywords in self.phq9_map.items() 
                             if any(re.search(rf'\b{re.escape(word)}\b', text.lower()) for word in keywords)]
        
        # Krok 5: Decyzja o statusie rozmowy
        status = "EMERGENCY" if risk_score > 0.7 else "CONVERSATION"

        # Zwrócenie kompletnego raportu w formacie JSON
        return {
            "status": status,
            "risk_score": round(risk_score, 4),
            "emotions": emotions_dict,
            "clinical_metrics": {
                "phq9_est": min(len(detected_symptoms) * 3, 27),  # Estymacja skali PHQ-9
                "symptoms": detected_symptoms
            }
        }