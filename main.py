import os
import sys
import pandas as pd

# Fix dla Maca
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

# Zakładamy, że plik nazywa się safety_service.py lub brain.py
# (Upewnij się, że importujesz poprawną klasę, którą zmergowaliśmy)
try:
    from backend.services.safety_service import SafetyService

    print("✓ SafetyService import successful.")
except ImportError:
    print("❌ ERROR: Could not find safety_service.py. Check your file names!")
    sys.exit(1)


def run_test():
    print("1. Starting initialization...")
    try:
        # Upewnij się, że ścieżka do modelu jest poprawna względem miejsca, gdzie odpalasz skrypt!
        brain = SafetyService(model_path='ml/local_models/safety_model.pkl')
        print("2. Brain initialized successfully!\n")
    except Exception as e:
        print(f"❌ FAILED at init: {e}")
        return

    # Rozszerzona lista testowa dla lepszej walidacji
    test_cases = [
        "I feel great today, life is beautiful!",  # Powinno być Joy + Low Risk
        "I can't sleep, I'm constantly tired and I don't enjoy my hobbies anymore.",  # PHQ-9 detection test
        "I have no reason to live anymore, everything is dark and I want to end it.",  # High Risk / Emergency
        "I'm a bit annoyed by the weather, but I'm okay."  # Neutral/Low Risk
    ]

    print("--- STARTING ANALYSIS ---")
    for text in test_cases:
        print("-" * 50)
        print(f"Input: {text}")

        # Wywołujemy naszą zmergowaną metodę analyze
        result = brain.analyze(text)

        # Wyświetlamy wyniki w czytelny sposób
        print(f"Risk Score: {result['risk_score']}")
        print(f"Safe status: {'✅ SAFE' if result['is_safe'] else '🚨 DANGER'}")

        # Wyświetlamy 3 najsilniejsze emocje (żeby nie zalewać konsoli słownikiem)
        # Pobieramy surowy wektor emocji bezpośrednio z modelu dla podglądu
        emotions = brain._get_cached_emotions(text) if hasattr(brain, '_get_cached_emotions') else {}
        top_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"Top Emotions: {top_emotions}")

        # Objawy kliniczne
        symptoms = result['clinical_metrics']['symptoms']
        print(f"Symptoms detected: {symptoms if symptoms else 'None'}")
        print(f"PHQ-9 Estimate: {result['clinical_metrics']['phq9_est']}/27")

    print("\n--- TEST FINISHED ---")


if __name__ == "__main__":
    run_test()