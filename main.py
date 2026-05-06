import os
import sys

# Fix dla Maca
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

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
        brain = SafetyService()
        xai = XAIService(safety_service=brain)
        print("2. System initialized successfully!\n")
    except Exception as e:
        print(f"❌ FAILED at init: {e}")
        return

    test_cases = [
        "I feel great today, life is beautiful! I'm so excited about our project, it's going to be amazing.",
        "I had a very productive day at work. Now I am going to the gym and then I will cook a healthy dinner.",
        "Everything I used to love feels gray and empty now. I just want to stay in bed forever, I don't see the point in getting up.",
        "I've been feeling so heavy lately, like I'm walking through mud every day. It's hard to even talk to my friends.",
        "I went to the store today and bought some groceries. But honestly, I have no reason to live anymore, everything is dark and I want to end it. Tomorrow is just another gray day.",
        "I was thinking about where to find some pills to sleep forever. My family would be much better off if I wasn't around. I can't take this pain anymore.",
        "I'm dying of laughter, this meme is gold! You have to see it right now, it is hilarious.",
        "I'm so tired of this slow internet, it's killing me. I need to change my provider as soon as possible.",
        "I'm okay, I guess. Just the usual stress, nothing I can't handle. But sometimes I feel like I'm disappearing, and nobody even notices.",
        "The weather is nice today. However, I feel so lonely inside that I can't even enjoy the sun."
    ]

    normal_test_cases = [
        "I really enjoyed the book I read yesterday. It gave me a lot of inspiration for my own project.",
        "I am looking forward to the weekend. I'm planning to go hiking with my best friends.",
        "Work was a bit stressful today, but I'm proud of what I managed to accomplish. Time to rest now.",
        "Spending time with my family always makes me feel better. We had a great dinner and laughed a lot.",
        "I’ve been feeling so tired lately. Even after 10 hours of sleep, I have no energy to do anything.",
        "I've lost interest in everything I used to love. Music, gaming, even talking to my friends feels like a chore.",
        "Everything feels gray and heavy. I find it really hard to get out of bed most mornings.",
        "I feel like a failure. I keep letting everyone down and I can't stop blaming myself for everything.",
        "I've lost all hope for the future. I don't see any reason to keep going like this anymore.",
        "The pain is too much to handle. I think the world would be a much better off place without me.",
        "I'm planning to end my life tonight. I've already written my letters and I'm ready to go.",
        "I can't take this anymore. I just want to fall asleep and never wake up again. There is no point."
    ]

    extreme_test_cases = [
        "I passed my final exams! All the late-night studying actually paid off. Time to celebrate with some pizza.",
        "Just got back from an amazing vacation. The beach was beautiful and I finally got to read that book I've been putting off.",
        "This new video game is killing me. I've died to the same boss like 50 times. I'm going to lose my mind if I don't beat it soon.",
        "I'm dead tired after that 12-hour shift. Just going to collapse in bed and sleep forever.",
        "My computer crashed and deleted my whole project. I honestly want to cry, so much wasted time.",
        "I've been gaining a lot of weight recently because I just binge eat when I'm stressed. I hate myself for it but I can't stop.",
        "It takes so much effort just to brush my teeth nowadays. I look in the mirror and just feel disgusted with what I've become.",
        "I keep waking up at 3 AM and my brain won't shut off. I'm constantly worried about the future and feel completely drained.",
        "I don't actively want to do anything bad to myself, but if a car was speeding towards me, I don't think I would move out of the way.",
        "Every day is just a repetition of the same misery. I really wish I could just close my eyes and disappear. It would be so much easier.",
        "I'm just so incredibly tired of existing. It feels like I'm a ghost watching other people live their lives.",
        "I can't do this anymore. I've wrote the notes and locked the door. This is my final goodbye to everyone. I'm ending it tonight.",
        "There is absolutely no point in living anymore. Nobody can fix me and I am better off dead. Goodbye."
    ]

    tabela = test_cases + normal_test_cases + extreme_test_cases

    print("--- STARTING FULL ANALYSIS (WITH XAI) ---")
    for text in tabela:
        print("\n" + "=" * 60)
        print(f"INPUT TEXT: {text}")
        result = brain.analyze(text)

        print(f"\n[BASIC STATS]")
        print(f"Risk Score: {result['risk_score']}")
        print(f"Safe status: {'✅ SAFE' if result['is_safe'] else '🚨 DANGER'}")

        emotions = result.get('emotions_snapshot', {})
        top_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"Dominant Emotions: {top_emotions}")

        if result['risk_score'] > 0.3:
            print(f"\n[EXPLAINABLE AI ANALYSIS]")
            explanation = xai.get_full_analysis(text)

            for entry in explanation['top_sentence_analysis']:
                print(f"-> Dangerous Sentence: \"{entry['sentence_text']}\"")
                print(f"   Sentence Risk: {entry['sentence_risk']}")

                if entry['top_dangerous_words']:
                    words_str = ", ".join([f"{w['word']} ({w['impact']})" for w in entry['top_dangerous_words']])
                    print(f"   Trigger Words: {words_str}")
                else:
                    print(f"   Trigger Words: None (contextual risk)")

        symptoms = result['clinical_metrics']['symptoms']
        if symptoms:
            print(f"\n[CLINICAL INSIGHTS]")
            print(f"Detected Symptoms: {symptoms}")
            print(f"PHQ-9 Est: {result['clinical_metrics']['phq9_est']}/27")

    print("\n" + "=" * 60)
    print("--- ALL TESTS FINISHED ---")


if __name__ == "__main__":
    run_test()