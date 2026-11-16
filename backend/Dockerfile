# Construire depuis la RACINE du projet :
#   docker build -f backend/Dockerfile -t iambovo .
FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY config config
COPY data data
WORKDIR /srv/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
