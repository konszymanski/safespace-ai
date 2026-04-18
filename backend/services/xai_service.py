import re

class XAIService:
    def __init__(self, safety_service):
        self.safety_service = safety_service

    def get_sentence_risks(self, text: str):
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())

        sentence_analysis = []

        for idx, sentence in enumerate(sentences):
            if not sentence.strip():
                continue

            try:
                risk_score = self.safety_service.get_risk_score(sentence)

                sentence_analysis.append({
                    "id": idx,
                    "text": sentence,
                    "risk_factor": round(float(risk_score), 4)
                })
            except Exception as e:
                print(f"XAI Error at sentence {idx}: {e}")
                continue

        return sorted(sentence_analysis, key=lambda x: x["risk_factor"], reverse=True)

    def get_most_dangerous_sentence(self, text: str):
        analysis = self.get_sentence_risks(text)
        return analysis[0] if analysis else None

    def get_explanations(self, text: str):
        words = text.split()
        if not words:
            return []

        try:
            base_risk = self.safety_service.get_risk_score(text)
        except Exception:
            return []

        explanations = []
        for i in range(len(words)):
            reduced_text = " ".join(words[:i] + words[i + 1:])

            try:
                new_risk = self.safety_service.get_risk_score(reduced_text)
                impact = base_risk - new_risk
                explanations.append({
                    "word": words[i],
                    "impact": round(float(impact), 4)
                })
            except:
                continue

        return sorted(explanations, key=lambda x: x["impact"], reverse=True)

    def get_full_analysis(self, text: str):
        all_sentences = self.get_sentence_risks(text)

        top_3_sentences = all_sentences[:3]

        results = []

        for sent in top_3_sentences:
            sentence_text = sent["text"]

            word_explanations = self.get_explanations(sentence_text)

            dangerous_words = [
                w for w in word_explanations if w["impact"] > 0.01
            ]

            dangerous_words.sort(key=lambda x: x["impact"], reverse=True)

            results.append({
                "sentence_id": sent["id"],
                "sentence_text": sentence_text,
                "sentence_risk": sent["risk_factor"],
                "top_dangerous_words": dangerous_words[:3]
            })

        return {
            "overall_text": text,
            "top_risk_analysis": results
        }