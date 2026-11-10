# Imagem única para a API (FastAPI) e o painel (Streamlit).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LEGALFLOW_DADOS=/dados \
    TZ=America/Sao_Paulo

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY legalflow ./legalflow
COPY painel ./painel
COPY exemplos ./exemplos
COPY .streamlit ./.streamlit

VOLUME ["/dados"]
