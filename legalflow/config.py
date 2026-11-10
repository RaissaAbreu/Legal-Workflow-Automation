"""Configurações lidas de variáveis de ambiente (lidas a cada chamada, para facilitar testes)."""

import os
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent


def dir_dados() -> Path:
    caminho = Path(os.getenv("LEGALFLOW_DADOS", RAIZ_PROJETO / "dados"))
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def caminho_banco() -> Path:
    return Path(os.getenv("LEGALFLOW_BANCO", dir_dados() / "legalflow.db"))


def dir_documentos() -> Path:
    caminho = dir_dados() / "documentos"
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def url_webhook_n8n() -> str:
    """URL do webhook de entrada do n8n (usada pelo painel na 'Nova demanda')."""
    return os.getenv("LEGALFLOW_N8N_WEBHOOK", "").strip()


def url_painel() -> str:
    return os.getenv("LEGALFLOW_URL_PAINEL", "http://localhost:8501").rstrip("/")


def teams_webhook_padrao() -> str:
    """Webhook do Teams usado quando a demanda não tem responsável com canal próprio."""
    return os.getenv("TEAMS_WEBHOOK_PADRAO", "").strip()


def dias_alerta_proximo() -> int:
    return int(os.getenv("LEGALFLOW_DIAS_ALERTA", "3"))


def horas_repeticao_vencida() -> int:
    return int(os.getenv("LEGALFLOW_HORAS_REPETICAO_VENCIDA", "24"))


def horas_alerta_prazo_a_definir() -> int:
    return int(os.getenv("LEGALFLOW_HORAS_PRAZO_A_DEFINIR", "24"))
