"""Identificação de urgência e sugestão de prioridade: prazo + palavras-chave.

Regra: prioridade final = a maior entre (prioridade pelo prazo) e (prioridade pelos termos).

Prazo (dias corridos até a data):
    vencido ou até 2 dias -> Crítica | 3 a 5 -> Alta | 6 a 15 -> Média | mais de 15 -> Baixa
    sem prazo informado   -> Média e a demanda é marcada como "prazo a definir"

Termos:
    críticos (liminar, tutela de urgência, mandado, bloqueio judicial...) -> Crítica
    altos (audiência, citação, intimação, auto de infração...)            -> Alta
    médios (notificação extrajudicial, Procon, ofício...)                 -> Média
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .constantes import PRIORIDADES
from .texto import contem_termo, normalizar

TERMOS_CRITICOS = [
    "liminar", "tutela de urgência", "tutela antecipada", "mandado de segurança", "mandado",
    "bloqueio judicial", "bloqueio de contas", "sisbajud", "busca e apreensão", "multa diária",
    "astreintes", "prazo fatal",
]
TERMOS_ALTOS = [
    "audiência", "citação", "intimação", "auto de infração", "autuação", "penhora",
    "vazamento de dados", "incidente de segurança", "urgente", "urgência", "sentença",
]
TERMOS_MEDIOS = [
    "notificação extrajudicial", "notificação", "procon", "reclamação", "ofício",
    "reclame aqui", "fiscalização",
]

LIMITES_PRAZO = [(2, "Crítica"), (5, "Alta"), (15, "Média")]


@dataclass
class ResultadoPrioridade:
    prioridade: str
    dias_ate_prazo: int | None
    prazo_a_definir: bool
    motivos: list[str] = field(default_factory=list)


def _nivel(prioridade: str) -> int:
    return PRIORIDADES.index(prioridade)


def prioridade_por_prazo(prazo: date | None, hoje: date) -> tuple[str, str]:
    if prazo is None:
        return "Média", "Sem prazo informado: prioridade base Média e prazo a definir"
    dias = (prazo - hoje).days
    if dias < 0:
        return "Crítica", f"Prazo vencido há {-dias} dia(s)"
    for limite, prioridade in LIMITES_PRAZO:
        if dias <= limite:
            return prioridade, f"Prazo em {dias} dia(s)"
    return "Baixa", f"Prazo em {dias} dia(s)"


def sugerir_prioridade(texto: str, prazo: date | None, hoje: date) -> ResultadoPrioridade:
    norm = normalizar(texto)
    prioridade, motivo_prazo = prioridade_por_prazo(prazo, hoje)
    motivos = [motivo_prazo]

    for termos, nivel in ((TERMOS_CRITICOS, "Crítica"), (TERMOS_ALTOS, "Alta"), (TERMOS_MEDIOS, "Média")):
        achados = [t for t in termos if contem_termo(norm, t)]
        if achados:
            motivos.append(f"Termos de urgência {nivel.lower()}: {', '.join(achados)}")
            if _nivel(nivel) > _nivel(prioridade):
                prioridade = nivel
            break  # só o grupo mais grave conta

    dias = (prazo - hoje).days if prazo else None
    return ResultadoPrioridade(prioridade, dias, prazo is None, motivos)
