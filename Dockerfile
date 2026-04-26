FROM python:3.12-slim

WORKDIR /app

# Dépendances Python
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    "fastapi>=0.111" \
    "uvicorn[standard]>=0.29" \
    "openpyxl>=3.1" \
    "matplotlib>=3.8"

# Code applicatif
COPY api/     api/
COPY scripts/ scripts/
COPY ui/      ui/

# Données de référence immuables (CSVs)
COPY data/budget/       data/budget/
COPY data/prestataires/ data/prestataires/

# data/factures/ et les répertoires de sortie sont fournis par le volume
# monté depuis l'hôte (voir docker-compose.yml : ./data:/app/data)
RUN mkdir -p data/factures \
             data/navettes_et_bons/mails \
             data/navettes_et_bons/rejets \
             data/tmp \
             data/vue_globale

EXPOSE 8000

# 0.0.0.0 requis dans le conteneur ; la restriction localhost
# est assurée par le port mapping 127.0.0.1:8000:8000 dans compose
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
