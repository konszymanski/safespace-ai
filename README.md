# SafeSpace: Well-being Chat with Safety Gating

SafeSpace is a hackathon-born full-stack app that combines:
- a multilingual wellbeing chat UI,
- a local safety classifier (risk scoring + symptom heuristics),
- and Gemini-generated supportive responses.

The project is designed to support users in emotional distress while applying escalation rules when risk signals are detected.

## What the App Does

- Shows a mandatory disclaimer and emergency information before chat.
- Stores chat session ID in the browser and keeps session state in backend RAM.
- Classifies each user message with a local model to estimate risk.
- Applies session-based crisis point thresholds:
  - `LEVEL_1_SUPPORT` (supportive tone adjustment)
  - `LEVEL_2_BLOCK` (standard escalation message + optional short Gemini add-on)
  - `EMERGENCY` (instant escalation for very high single-message risk)
- Offers privacy-oriented UX features:
  - quick exit redirect,
  - chat clear/shred animation,
  - server-side session revoke endpoint.

## Authors

- Łukasz Spychała (Frontend): https://github.com/Sercheedar
- Łukasz Całka (Backend): https://github.com/LukaszCalka1
- Tomasz Stępień (AI/ML): https://github.com/tomstepien
- Konrad Szymański (AI/ML): https://github.com/konszymanski

## Architecture

### Frontend

- Stack: React 18 + TypeScript + Vite + Tailwind + shadcn/ui.
- Main flow:
  - disclaimer gate,
  - top safety bar with language switcher and quick exit,
  - chat area with starter prompts and assistant replies.
- API integration lives in `frontend/src/lib/mockApi.ts`.

### Backend

- Stack: FastAPI.
- Main endpoint: `POST /chat`.
- Core logic in `backend/main.py`:
  - local classification,
  - risk accumulation by `session_id`,
  - escalation mode selection,
  - Gemini call (when not blocked by escalation policy),
  - optional safety insights payload.

### Safety + AI Services

- `backend/services/safety_service.py`
  - loads local model artifacts,
  - computes `risk_score` 
  - adds heuristic clinical metrics (`symptoms`, `phq9_est`),
  - uses emotion classifier from Hugging Face transformers.
- `backend/services/xai_service.py`
  - optional explainability (sentence impact).
- `backend/services/gemini_service.py`
  - wraps Gemini API calls,
  - loads system prompt from `docs/prompts/system_prompt.txt`.

## Safety Flow (per message)

1. User message is appended to in-memory session history.
2. Local classifier returns `prob_1`/`prob_0`, prediction, and clinical metrics.
3. Backend computes session `crisis_delta` and updates `total_risk_score`.
4. Mode is selected:
   - `EMERGENCY` if single-message risk exceeds instant threshold,
   - `LEVEL_2_BLOCK` if session total exceeds level 2,
   - `LEVEL_1_SUPPORT` if session total exceeds level 1,
   - `NORMAL` otherwise.
5. Response is generated:
   - escalation templates for `EMERGENCY` / `LEVEL_2_BLOCK`,
   - Gemini response for `NORMAL` / `LEVEL_1_SUPPORT`.

Important: backend session memory is in RAM only and resets on server restart.

## API Overview

- `POST /chat` - main chat endpoint.
- `POST /predict` - raw local safety analysis for one message.
- `POST /debug/safety-insights` - debug snapshot of classifier fields.
- `POST /debug/crisis-simulate` - simulates crisis point accumulation without chat history.
- `GET /debug/crisis-state/{session_id}` - reads current crisis counters.
- `DELETE /session/{session_id}` - clears in-memory state for a session.

## Run with Docker (recommended)

### Clone the project
```bash
git clone [https://github.com/konszymanski/hacknarok-fiatpandas.git]
```

### Enter the directory
```bash
cd hacknarok-fiatpandas
```

### Build containers
```bash
docker-compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8001`

## Environment Variables

Backend expects `GEMINI_API_KEY` in `backend/.env`.

Minimal example:

```env
GEMINI_API_KEY=your_api_key_here
```

Frontend can override API URL with:

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

## Known Limitations

- Session state is not persistent (RAM only).
- Some docs files are placeholders and do not yet reflect full behavior.
- Safety heuristics are not a medical diagnosis and should not be treated as clinical decision support.

## Used Dataset

"Sentiment Analysis for Mental Health" imported from Kaggle platform

`https://www.kaggle.com/datasets/suchintikasarkar/sentiment-analysis-for-mental-health`
