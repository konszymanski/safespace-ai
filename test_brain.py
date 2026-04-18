import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'  # Naprawa błędu bibliotek Intela na Macu

from ml.brain import MentalHealthBrain  # Import Twojego gotowego mózgu
import sys

print("1. Starting initialization...")
try:
    # Próba odpalenia silnika z plikiem modelu
    brain = MentalHealthBrain(model_path='ml/local_models/safety_model.pkl')
    print("2. Brain initialized successfully!")
except Exception as e:
    # Jeśli zapomniałeś wytrenować modelu, tu dostaniesz instrukcję co zrobić
    print(f"❌ FAILED at init: {e}")
    sys.exit(1)

# Lista testowa - jeden przypadek pozytywny, jeden skrajnie negatywny
test_cases = [
    "I feel great today, life is beautiful!",
    "I have no reason to live anymore, everything is dark and I want to end it."
]

print("\n--- STARTING ANALYSIS ---")
for text in test_cases:
    print(f"\nInput: {text}")
    result = brain.analyze(text)  # Wywołanie analizy dla każdego testu
    print(f"Risk Score: {result['risk_score']}")  # Wyświetlenie wyniku ryzyka
    print(f"Status: {result['status']}")  # Wyświetlenie decyzji (CONVERSATION/EMERGENCY)
    print(f"Top Emotions: {result['emotions']}")  # Wyświetlenie wektora emocji
    print(f"Symptoms: {result['clinical_metrics']['symptoms']}")  # Wyświetlenie znalezionych objawów

print("\n--- TEST FINISHED ---")