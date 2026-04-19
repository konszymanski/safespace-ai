# hacknarok-fiatpandas

Czat wspierający (frontend Vite + React) z backendem FastAPI: lokalny model klasyfikacyjny + Gemini.

## Wymagania

- [Docker](https://docs.docker.com/get-docker/) z **Docker Compose v2** (`docker compose`).

## Szybki start (Docker)

1. Sklonuj repozytorium i wejdź w katalog główny projektu (obok `docker-compose.yml`).

2. Utwórz plik **`backend/.env`** z kluczem do Gemini (wzorzec: `backend/.env.example`):

   ```bash
   cp backend/.env.example backend/.env
   ```

   (Windows PowerShell: `Copy-Item backend\.env.example backend\.env`)

   Uzupełnij `GEMINI_API_KEY=...`

3. Uruchom stack (pierwsze uruchomienie może chwilę trwać):

   ```bash
   docker compose up --build
   ```

4. W przeglądarce:

    **Frontend**  | http://localhost:5173          
    **API (REST)**| http://localhost:8001        
    **Swagger UI**| http://localhost:8001/docs     

Frontend ma ustawione `VITE_API_BASE_URL=http://localhost:8001` (w `docker-compose.yml`), więc przeglądarka na hoście woła API pod tym samym adresem.

## Zatrzymanie

W terminalu: `Ctrl+C`, ewentualnie `docker compose down`. Named volume z `node_modules` frontu i cache HF zostają do kolejnego `up` (szybszy restart).

## Opcjonalnie: bez Dockera

- Backend: katalog `backend/`, venv, `pip install -r requirements.txt`, zmienne z `backend/.env`, potem np. `uvicorn main:app --host 0.0.0.0 --port 8001 --reload`.
- Frontend: katalog `frontend/`, `npm install`, `npm run dev` — domyślnie Vite pod `http://localhost:5173`; ustaw `VITE_API_BASE_URL` jeśli API nie jest na `http://127.0.0.1:8001`.
