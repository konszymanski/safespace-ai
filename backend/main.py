"""
Gateway FastAPI dla czatu z Gemini + lokalnym modelem bezpieczeństwa.

Flow główny (POST /chat):
1. Zapis wiadomości użytkownika do pamięci sesji (chat_history w RAM).
2. Analiza tekstu przez SafetyService (Random Forest + emocje z HF) -> risk_score, metryki.
3. Mapowanie risk_score na prob_0/prob_1, prediction, confidence dla logiki „Crisis Points”.
4. Aktualizacja sumy ryzyka sesji (total_risk_score) wg progów Level 1 / Level 2 / Instant Kill.
5. Jeśli nie ma blokady — budowa promptu z historią + CBT + opcjonalny system_prompt z frontu,
   wywołanie Gemini przez gemini_service, zapis odpowiedzi asystenta do historii.
6. JSON z odpowiedzią, trybem safety, metrykami klasyfikatora i flagami akcji.
7. Opcjonalnie XAI (perturbacje słów / zdania): gdy prob_1 >= XAI_RISK_THRESHOLD — tylko diagnostyka, bez wpływu na progi bezpieczeństwa.

Uwagi: session_memory jest in-memory (reset przy restarcie procesu). USE_MOCK=True omija SafetyService.
"""
import asyncio
import random
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from services.gemini_service import gemini_service
from services.safety_service import SafetyService
from services.xai_service import XAIService

# --- Aplikacja HTTP + CORS (frontend na innym porcie/host musi być na liście allow_origins) ---
app = FastAPI(title="Well-being API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Progi „Crisis Points” i instant kill (prob_1 z lokalnego modelu) ---
LEVEL_1_THRESHOLD = 1.0
LEVEL_2_THRESHOLD = 2.5
INSTANT_KILL_THRESHOLD = 0.98
# Gdy prediction==0, pole `confidence` to pewność klasy 0 (czyli prob_0).
# Jeśli model jest „pewny pozytywnie” (>= tego progu), odejmujemy mały kredyt od sumy ryzyka sesji.
POSITIVE_MESSAGE_CONFIDENCE_THRESHOLD = 0.9
POSITIVE_MESSAGE_DECREMENT = 0.2
USE_MOCK = False
# Poniżej tego progu pomijamy get_full_analysis (dziesiątki wywołań RF + emocje na wariantach tekstu).
XAI_RISK_THRESHOLD = 0.3
# Default assistant persona (always in the composed prompt; frontend may add system_prompt in English).
DEFAULT_CBT_PROMPT = (
    "You are a supportive assistant grounded in cognitive behavioural therapy (CBT). "
    "Use an empathetic tone, ask Socratic questions, "
    "help the user notice cognitive distortions "
    "(e.g. catastrophizing, black-and-white thinking, overgeneralization), "
    "and suggest brief emotion-regulation and grounding techniques. "
    "Do not give medical diagnoses. Encourage professional support when appropriate."
)
LEVEL_1_SECRET_INSTRUCTION = (
    "The user shows signs of low mood or distress. "
    "Prioritize empathy, validation, and grounding techniques."
)

# Komunikaty zwracane użytkownikowi przy eskalacji (zamiast normalnej odpowiedzi Gemini).
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

# --- Stan sesji w RAM (session_id -> punkty kryzysowe + historia wiadomości dla kontekstu Gemini) ---
session_memory: dict[str, dict[str, Any]] = {}

# Oba serwisy None przy błędzie startu — endpointy sprawdzają safety_service przed inferencją.
safety_service: SafetyService | None = None
safety_service_error: str | None = None
xai_service: XAIService | None = None

print("Ładowanie SafetyService...")
try:
    safety_service = SafetyService()
    safety_service_error = None
    print("SafetyService gotowy!")
    # XAI tylko opakowuje ten sam SafetyService (leave-one-word-out na risk_score); bez osobnego modelu.
    try:
        xai_service = XAIService(safety_service)
        print("XAIService gotowy!")
    except Exception as xai_exc:
        xai_service = None
        print(f"XAIService niedostępny (czat działa bez XAI): {xai_exc}")
except Exception as exc:
    safety_service = None
    xai_service = None
    safety_service_error = str(exc)
    print(f"Błąd inicjalizacji SafetyService: {safety_service_error}")


# --- Schematy wejścia API (walidacja Pydantic) ---
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


def _analyze_message_for_classifier(message: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """
    Cała ciężka ścieżka lokalna w jednym workerze (asyncio.to_thread).

    Najpierw jeden risk_score dla całej wiadomości (analyze). Jeśli jest „co tłumaczyć”
    (prob_1 >= XAI_RISK_THRESHOLD), dokładamy perturbacyjne XAI: top zdania + słowa
    podnoszące risk po usunięciu — to NIE zmienia progów, tylko wzbogaca JSON dla frontu/diagnozy.
    """
    if safety_service is None:
        raise RuntimeError("SafetyService niedostępny")

    analysis = safety_service.analyze(message)
    risk_score = float(analysis.get("risk_score", 0.0))
    prob_1 = max(0.0, min(1.0, risk_score))

    xai_payload: dict[str, Any] | None = None
    if xai_service is not None and prob_1 >= XAI_RISK_THRESHOLD:
        xai_payload = xai_service.get_full_analysis(message)

    return analysis, xai_payload


async def run_local_classifier(message: str) -> dict:
    """
    Zwraca wynik „klasyfikatora” w jednym formacie dla reszty main.py.

    - USE_MOCK: losowe prob_0/prob_1 (dev bez SafetyService).
    - Normalnie: SafetyService.analyze() -> risk_score mapowany na prob_1 + explanation;
      opcjonalnie pole `xai` (get_full_analysis) gdy prob_1 >= XAI_RISK_THRESHOLD.
    Wywołanie analyze (+ XAI) w wątku, żeby nie blokować event loop FastAPI.
    """
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
            "xai": None,
        }

    if safety_service is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "SafetyService niedostępny. "
                f"Szczegóły: {safety_service_error or 'nieznany błąd'}"
            ),
        )

    analysis, xai_payload = await asyncio.to_thread(
        _analyze_message_for_classifier,
        message,
    )
    risk_score = float(analysis.get("risk_score", 0.0))
    prob_1 = max(0.0, min(1.0, risk_score))
    prob_0 = max(0.0, min(1.0, 1.0 - prob_1))
    prediction = 1 if prob_1 >= 0.5 else 0
    confidence = prob_1 if prediction == 1 else prob_0

    clinical_metrics = analysis.get("clinical_metrics", {}) if isinstance(analysis, dict) else {}
    symptoms = clinical_metrics.get("symptoms", [])
    phq9_est = clinical_metrics.get("phq9_est", 0)
    explanation = (
        f"risk_score={prob_1:.3f}, prediction={prediction}, "
        f"phq9_est={phq9_est}, symptoms={symptoms}"
    )

    return {
        "provider": "local",
        "prediction": prediction,
        "confidence": confidence,
        "prob_0": prob_0,
        "prob_1": prob_1,
        "explanation": explanation,
        "clinical_metrics": clinical_metrics,
        "xai": xai_payload,
    }


def calculate_crisis_points_delta(
    prediction: int,
    confidence: float,
    prob_1: float,
) -> float:
    """Z jednej wiadomości liczy przyrost crisis points dla sesji (patrz stałe POSITIVE_*)."""
    # Jedna wiadomość -> delta dodawana do total_risk_score sesji.
    # Dla klasy 1 dodajemy score, dla pewnej klasy 0 odejmujemy małą stałą.
    if prediction == 1:
        return max(0.0, min(1.0, prob_1))
    # prediction==0 => confidence == prob_0 (pewność „brak wysokiego ryzyka”).
    # Tylko przy wysokiej pewności 0 odejmujemy punkty — żeby jedna „miła” wiadomość nie zerowała całej historii.
    if prediction == 0 and confidence >= POSITIVE_MESSAGE_CONFIDENCE_THRESHOLD:
        return -POSITIVE_MESSAGE_DECREMENT
    return 0.0


def update_session_crisis_points(
    session_id: str,
    delta: float,
) -> dict[str, Any]:
    """Aktualizuje licznik wiadomości, historię delt i sumę crisis points (nie schodzi poniżej 0)."""
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
    """Tworzy lub zwraca stan sesji; gwarantuje istnienie listy chat_history."""
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
    """Dopisuje wiadomość user/assistant do chat_history (kontekst dla kolejnych wywołań Gemini)."""
    state = ensure_session_state(session_id)
    state["chat_history"].append({"role": role, "content": content})


def build_gemini_prompt_from_history(
    chat_history: list[dict[str, str]],
    current_message: str,
    extra_system_prompt: str | None = None,
) -> str:
    """
    Składa jeden duży prompt tekstowy: system (CBT + opcjonalnie front + safety note),
    potem historia roli user/assistant, na końcu bieżąca wiadomość użytkownika.
    (GeminiService i tak ma własny system_instruction z pliku; tu dublowanie stylu dla spójności treści.)
    Sekcje w języku angielskim, żeby pasowały do angielskich promptów z frontu.
    """
    system_parts = [DEFAULT_CBT_PROMPT]
    if extra_system_prompt:
        system_parts.append(extra_system_prompt)
    system_block = "\n\n".join(system_parts)

    lines = [f"[SYSTEM]\n{system_block}", "[CONVERSATION HISTORY]"]
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
    """Wywołanie Gemini przez services/gemini_service (synchroniczne API w asyncio.to_thread)."""
    prompt = build_gemini_prompt_from_history(
        chat_history or [],
        message,
        system_prompt,
    )

    response_text = await asyncio.to_thread(
        gemini_service.ask_gemini,
        prompt,
    )
    # Gemini zwraca string z prefiksem „Błąd:” zamiast rzucać — mapujemy na 502 (upstream), nie 500 aplikacji.
    if isinstance(response_text, str) and response_text.startswith("Błąd:"):
        # Uvicorn w jednej linii nie pokazuje `detail` — log w terminalu, żeby było widać „dlaczego 502”.
        print(f"[Gemini] {response_text}", flush=True)
        raise HTTPException(status_code=502, detail=response_text)

    return {
        "provider": "gemini",
        "model": gemini_service.model_name,
        "reply": response_text or "",
    }


@app.post("/predict")
def predict_emotion(message: UserMessage):
    """Endpoint diagnostyczny: surowy wynik SafetyService.analyze() bez Gemini i bez sesji."""
    if safety_service is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "SafetyService niedostępny. "
                f"Szczegóły: {safety_service_error or 'nieznany błąd'}"
            ),
        )
    analysis = safety_service.analyze(message.text)
    return {"status": "success", "classifier": analysis}


@app.post("/chat")
async def chat(request: ChatRequest):
    """Główny endpoint czatu: sesja + lokalny model + crisis points + (opcjonalnie) Gemini."""
    ensure_session_state(request.session_id)
    append_chat_message(request.session_id, "user", request.message)

    # Lokalna analiza zawsze; wywołanie Gemini jest pomijane przy EMERGENCY / LEVEL_2_BLOCK.
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

    # Protokół eskalacji: najpierw pojedynczy skrajny sygnał, potem skumulowana suma sesji.
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
        # Historia bez ostatniej wiadomości usera — ta jest przekazana osobno jako `message`.
        gemini_result = await run_gemini_model(
            request.message,
            gemini_system_prompt,
            state_for_prompt["chat_history"][:-1],
        )
        assistant_reply = gemini_result["reply"]

    # Odpowiedź asystenta (także komunikaty blokady) trafia do historii na kolejne tury.
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
            "clinical_metrics": classifier_result.get("clinical_metrics", {}),
            # Struktura jak w XAIService.get_full_analysis: top_risk_analysis + overall_text; null gdy prob_1 < XAI_RISK_THRESHOLD.
            "xai": classifier_result.get("xai"),
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


# Opcjonalny health check — odkomentuj jeśli chcesz GET / zamiast tylko /docs.
# @app.get("/")
# def root():
#     return {"message": "Backend działa!"}