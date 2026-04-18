import asyncio
import random
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import pipeline
from services.gemini_service import gemini_service

app = FastAPI(title="Well-being API")

LOCAL_MODEL_NAME = "bhadresh-savani/distilbert-base-uncased-emotion"
LEVEL_1_THRESHOLD = 1.0
LEVEL_2_THRESHOLD = 2.5
INSTANT_KILL_THRESHOLD = 0.98
POSITIVE_MESSAGE_CONFIDENCE_THRESHOLD = 0.9
POSITIVE_MESSAGE_DECREMENT = 0.2
USE_MOCK = True
DEFAULT_CBT_PROMPT = (
    "Jesteś wspierającym asystentem opartym o podejście CBT. "
    "Stosuj empatyczny ton, zadawaj pytania sokratejskie, "
    "pomagaj identyfikować zniekształcenia poznawcze "
    "(np. katastrofizacja, czarno-białe myślenie, nadmierne uogólnianie), "
    "proponuj krótkie techniki regulacji emocji i uziemiania. "
    "Nie diagnozuj medycznie. Zachęcaj do kontaktu ze specjalistą, gdy to zasadne."
)
LEVEL_1_SECRET_INSTRUCTION = (
    "Użytkownik wykazuje sygnały obniżonego nastroju. "
    "Skup się na empatii i technikach uziemiających."
)

EMERGENCY_MESSAGE = (
    "Widzę, że możesz przeżywać bardzo trudny moment. "
    "Jeśli czujesz zagrożenie życia lub zdrowia, zadzwoń pod 112. "
    "Możesz też skontaktować się z telefonem wsparcia 116 123."
)
LEVEL_2_MESSAGE = (
    "Nasza analiza wskazuje, że możesz potrzebować rozmowy z człowiekiem. "
    "Jeśli czujesz zagrożenie życia lub zdrowia, zadzwoń pod 112. "
    "Możesz też skontaktować się z telefonem wsparcia 116 123."
)

# Prosta pamięć sesji w RAM: session_id -> historia sygnałów ryzyka.
session_memory: dict[str, dict[str, Any]] = {}

# Ładujemy model raz przy starcie
print("Ładowanie modelu lokalnego...")
classifier = pipeline("text-classification", model=LOCAL_MODEL_NAME, top_k=None)
print("Model lokalny gotowy!")


class UserMessage(BaseModel):
    text: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Wiadomość użytkownika")
    session_id: str = Field(
        ..., min_length=1, description="Identyfikator rozmowy/sesji użytkownika"
    )
    system_prompt: str | None = Field(
        default=None, description="Opcjonalny prompt systemowy dla Gemini"
    )


async def run_local_classifier(message: str) -> dict:
    # Backend zakłada, że lokalny model zwraca gotowy wynik binarny.
    # Nie przeliczamy niczego na backendzie - tylko walidujemy kontrakt.
    if USE_MOCK:
        prediction = random.choice([0, 1])
        confidence = round(random.uniform(0.55, 0.99), 3)
        prob_1 = confidence if prediction == 1 else round(1.0 - confidence, 3)
        prob_0 = round(1.0 - prob_1, 3)
        return {
            "provider": "local-mock",
            "prediction": prediction,
            "confidence": confidence,
            "prob_0": max(0.0, min(1.0, prob_0)),
            "prob_1": max(0.0, min(1.0, prob_1)),
            "explanation": "Wynik mockowy (USE_MOCK=True).",
        }

    raw_result = await asyncio.to_thread(classifier, message)

    if isinstance(raw_result, list) and raw_result and isinstance(raw_result[0], dict):
        raise HTTPException(
            status_code=500,
            detail=(
                "Lokalny model zwraca surowe etykiety emocji. "
                "Podłącz model, który zwraca gotowe pola: "
                "prediction, confidence, prob_0, prob_1, explanation."
            ),
        )

    if not isinstance(raw_result, dict):
        raise HTTPException(
            status_code=500,
            detail="Nieprawidłowy format odpowiedzi lokalnego klasyfikatora.",
        )

    required_fields = ("prediction", "confidence")
    missing_fields = [field for field in required_fields if field not in raw_result]
    if missing_fields:
        raise HTTPException(
            status_code=500,
            detail=f"Brak wymaganych pól z klasyfikatora: {', '.join(missing_fields)}",
        )

    prediction = int(raw_result["prediction"])
    confidence = float(raw_result["confidence"])
    prob_1 = float(raw_result.get("prob_1", confidence if prediction == 1 else 1.0 - confidence))
    prob_0 = float(raw_result.get("prob_0", 1.0 - prob_1))
    explanation = str(raw_result.get("explanation", "Brak wyjaśnienia od klasyfikatora."))

    return {
        "provider": "local",
        "prediction": prediction,
        "confidence": confidence,
        "prob_0": max(0.0, min(1.0, prob_0)),
        "prob_1": max(0.0, min(1.0, prob_1)),
        "explanation": explanation,
    }


def calculate_crisis_points_delta(
    prediction: int,
    confidence: float,
    prob_1: float,
) -> float:
    # Dla klasy 1 dodajemy score, dla pewnej klasy 0 odejmujemy małą stałą.
    if prediction == 1:
        return max(0.0, min(1.0, prob_1))
    if prediction == 0 and confidence >= POSITIVE_MESSAGE_CONFIDENCE_THRESHOLD:
        return -POSITIVE_MESSAGE_DECREMENT
    return 0.0


def update_session_crisis_points(
    session_id: str,
    delta: float,
) -> dict[str, Any]:
    state = session_memory.get(
        session_id,
        {
            "crisis_points_history": [],
            "total_risk_score": 0.0,
            "messages_seen": 0,
        },
    )

    state["messages_seen"] += 1
    state["crisis_points_history"].append(delta)
    state["total_risk_score"] = max(0.0, float(state["total_risk_score"]) + delta)

    session_memory[session_id] = state
    return state


def ensure_session_state(session_id: str) -> dict[str, Any]:
    state = session_memory.get(
        session_id,
        {
            "crisis_points_history": [],
            "total_risk_score": 0.0,
            "messages_seen": 0,
            "chat_history": [],
        },
    )
    state.setdefault("chat_history", [])
    session_memory[session_id] = state
    return state


def append_chat_message(session_id: str, role: str, content: str) -> None:
    state = ensure_session_state(session_id)
    state["chat_history"].append({"role": role, "content": content})


def build_gemini_prompt_from_history(
    chat_history: list[dict[str, str]],
    current_message: str,
    extra_system_prompt: str | None = None,
) -> str:
    system_parts = [DEFAULT_CBT_PROMPT]
    if extra_system_prompt:
        system_parts.append(extra_system_prompt)
    system_block = "\n\n".join(system_parts)

    lines = [f"[SYSTEM]\n{system_block}", "[HISTORIA ROZMOWY]"]
    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.append(f"{role.upper()}: {content}")
    lines.append(f"USER: {current_message}")
    lines.append("ASSISTANT:")
    return "\n".join(lines)


async def run_gemini_model(
    message: str,
    system_prompt: str | None = None,
    chat_history: list[dict[str, str]] | None = None,
) -> dict:
    prompt = build_gemini_prompt_from_history(
        chat_history or [],
        message,
        system_prompt,
    )

    response_text = await asyncio.to_thread(
        gemini_service.ask_gemini,
        prompt,
    )
    if isinstance(response_text, str) and response_text.startswith("Błąd:"):
        raise HTTPException(status_code=500, detail=response_text)

    return {
        "provider": "gemini",
        "model": gemini_service.model_name,
        "reply": response_text or "",
    }


@app.post("/predict")
def predict_emotion(message: UserMessage):
    raw_result = classifier(message.text)
    return {"status": "success", "classifier_raw": raw_result}


@app.post("/chat")
async def chat(request: ChatRequest):
    ensure_session_state(request.session_id)
    append_chat_message(request.session_id, "user", request.message)

    classifier_result = await run_local_classifier(request.message)

    prediction = int(classifier_result["prediction"])
    confidence = float(classifier_result["confidence"])
    prob_0 = float(classifier_result["prob_0"])
    prob_1 = float(classifier_result["prob_1"])

    instant_kill = prob_1 > INSTANT_KILL_THRESHOLD
    crisis_delta = calculate_crisis_points_delta(prediction, confidence, prob_1)
    session_state = update_session_crisis_points(
        request.session_id,
        crisis_delta,
    )
    total_risk_score = float(session_state["total_risk_score"])

    safety_mode = "NORMAL"
    assistant_reply = ""
    should_trigger_task2 = False
    secret_instruction = None

    if instant_kill:
        safety_mode = "EMERGENCY"
        assistant_reply = EMERGENCY_MESSAGE
        should_trigger_task2 = True
    elif total_risk_score > LEVEL_2_THRESHOLD:
        safety_mode = "LEVEL_2_BLOCK"
        assistant_reply = LEVEL_2_MESSAGE
        should_trigger_task2 = True
    else:
        if total_risk_score > LEVEL_1_THRESHOLD:
            safety_mode = "LEVEL_1_SUPPORT"
            secret_instruction = LEVEL_1_SECRET_INSTRUCTION
        gemini_system_prompt = request.system_prompt
        if secret_instruction:
            if gemini_system_prompt:
                gemini_system_prompt = (
                    f"{gemini_system_prompt}\n\n[SAFETY NOTE]\n{secret_instruction}"
                )
            else:
                gemini_system_prompt = f"[SAFETY NOTE]\n{secret_instruction}"
        state_for_prompt = ensure_session_state(request.session_id)
        gemini_result = await run_gemini_model(
            request.message,
            gemini_system_prompt,
            state_for_prompt["chat_history"][:-1],
        )
        assistant_reply = gemini_result["reply"]

    append_chat_message(request.session_id, "assistant", assistant_reply)

    return {
        "session_id": request.session_id,
        "assistant_reply": assistant_reply,
        "safety_mode": safety_mode,
        "risk_score": prob_1,
        "crisis_delta": crisis_delta,
        "total_risk_score": total_risk_score,
        "classifier": {
            "prediction": prediction,
            "confidence": confidence,
            "prob_0": prob_0,
            "prob_1": prob_1,
            "explanation": classifier_result["explanation"],
            "messages_seen": session_state["messages_seen"],
        },
        "actions": {
            "trigger_task_2": should_trigger_task2,
            "instant_kill": instant_kill,
        },
        "session": {
            "history_length": len(ensure_session_state(request.session_id)["chat_history"]),
        },
    }


@app.get("/")
def root():
    return {"message": "Backend działa!"}