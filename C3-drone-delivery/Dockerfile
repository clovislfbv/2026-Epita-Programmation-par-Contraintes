# Utilisation d'une image Python légère
FROM python:3.11-slim

# Définition du répertoire de travail
WORKDIR /app

# Installation des dépendances système nécessaires (si besoin pour certaines libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copie du fichier des dépendances
COPY requirements.txt .

# Installation des librairies Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source (backend et frontend)
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# On se place dans le dossier backend pour que les imports relatifs fonctionnent
WORKDIR /app/backend

# Exposition du port utilisé par FastAPI
EXPOSE 8000

# Commande de lancement avec Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
