FROM python:3.12-slim

WORKDIR /app

# Instalacja zależności systemowych, by uniknąć błędów przy kompilacji niektórych paczek
RUN apt-get update && apt-get install -y build-essential

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kod będzie mapowany przez wolumen (docker-compose), 
# ale COPY jest dobrą praktyką na wypadek wdrożenia na produkcję
COPY . .