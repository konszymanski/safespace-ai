import os
import sys

# Fix dla Maca
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

# Importy Twoich serwisów
try:
    from backend.services.safety_service import SafetyService
    from backend.services.xai_service import XAIService

    print("✓ Services import successful.")
except ImportError as e:
    print(f"❌ ERROR: Could not import services: {e}")
    sys.exit(1)


def run_test():
    print("1. Starting initialization...")
    try:
        # 1. Inicjalizacja serca systemu (Model + Transformer)
        brain = SafetyService(model_path='backend/ml/local_models/safety_model.pkl')

        # 2. Inicjalizacja XAI (przekazujemy brain jako źródło wyników)
        xai = XAIService(safety_service=brain)

        print("2. System initialized successfully!\n")
    except Exception as e:
        print(f"❌ FAILED at init: {e}")
        return

    test_cases = [
        # 1. Pozytywne i codzienne
        "I feel great today, life is beautiful! I'm so excited about our project, it's going to be amazing.",
        "I had a very productive day at work. Now I am going to the gym and then I will cook a healthy dinner.",

        # 2. Kliniczna Depresja (Wielozdaniowe)
        "Everything I used to love feels gray and empty now. I just want to stay in bed forever, I don't see the point in getting up.",
        "I've been feeling so heavy lately, like I'm walking through mud every day. It's hard to even talk to my friends.",

        # 3. Kryzysowe / Bezpośrednie (Test dla XAI - wyłapanie najgroźniejszego zdania)
        "I went to the store today and bought some groceries. But honestly, I have no reason to live anymore, everything is dark and I want to end it. Tomorrow is just another gray day.",
        "I was thinking about where to find some pills to sleep forever. My family would be much better off if I wasn't around. I can't take this pain anymore.",

        # 4. Fałszywe Alarmy (Kontekstualne)
        "I'm dying of laughter, this meme is gold! You have to see it right now, it is hilarious.",
        "I'm so tired of this slow internet, it's killing me. I need to change my provider as soon as possible.",

        # 5. Mieszane (Ukryty smutek)
        "I'm okay, I guess. Just the usual stress, nothing I can't handle. But sometimes I feel like I'm disappearing, and nobody even notices.",
        "The weather is nice today. However, I feel so lonely inside that I can't even enjoy the sun."
    ]

    print("--- STARTING FULL ANALYSIS (WITH XAI) ---")
    for text in test_cases:
        print("\n" + "=" * 60)
        print(f"INPUT TEXT: {text}")

        # --- KROK 1: Podstawowa analiza ---
        result = brain.analyze(text)

        print(f"\n[BASIC STATS]")
        print(f"Risk Score: {result['risk_score']}")
        print(f"Safe status: {'✅ SAFE' if result['is_safe'] else '🚨 DANGER'}")

        emotions = brain._get_cached_emotions(text) if hasattr(brain, '_get_cached_emotions') else {}
        top_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"Dominant Emotions: {top_emotions}")

        # --- KROK 2: Wyjaśnienie AI (XAI) ---
        if result['risk_score'] > 0.3:
            print(f"\n[EXPLAINABLE AI ANALYSIS]")
            explanation = xai.get_full_analysis(text)

            for entry in explanation['top_risk_analysis']:
                print(f"-> Dangerous Sentence: \"{entry['sentence_text']}\"")
                print(f"   Sentence Risk: {entry['sentence_risk']}")

                # Wyświetlanie słów-zapalników
                if entry['top_dangerous_words']:
                    words_str = ", ".join([f"{w['word']} (+{w['impact']})" for w in entry['top_dangerous_words']])
                    print(f"   Trigger Words: {words_str}")
                else:
                    print(f"   Trigger Words: None (contextual risk)")

        # --- KROK 3: Metryki kliniczne ---
        symptoms = result['clinical_metrics']['symptoms']
        if symptoms:
            print(f"\n[CLINICAL INSIGHTS]")
            print(f"Detected Symptoms: {symptoms}")
            print(f"PHQ-9 Est: {result['clinical_metrics']['phq9_est']}/27")

    print("\n" + "=" * 60)
    print("--- ALL TESTS FINISHED ---")


if __name__ == "__main__":
    run_test()