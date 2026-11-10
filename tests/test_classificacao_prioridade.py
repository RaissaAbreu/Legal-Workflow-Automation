from datetime import date, timedelta

import pytest

from legalflow.classificacao import classificar
from legalflow.prioridade import sugerir_prioridade

HOJE = date(2026, 11, 10)


@pytest.mark.parametrize("texto, area", [
    ("Reclamação trabalhista de ex-funcionário pedindo horas extras e FGTS", "Trabalhista"),
    ("Ação de indenização por danos materiais em acidente; petição inicial anexa", "Cível"),
    ("Cliente registrou reclamação no Procon por cobrança indevida", "Consumidor"),
    ("Revisão da minuta do contrato e do aditivo com o fornecedor", "Contratual"),
    ("Ofício da ANPD sobre incidente de segurança com dados pessoais (LGPD)", "Regulatória"),
])
def test_classifica_cada_area(texto, area):
    resultado = classificar(texto)
    assert resultado.area == area
    assert resultado.confianca > 0.5


def test_texto_sem_termos_nao_classificado():
    resultado = classificar("Gostaria de marcar uma reunião sobre a política de viagens")
    assert resultado.area == "Não classificada"
    assert resultado.confianca == 0


def test_termos_sem_acento_tambem_contam():
    assert classificar("reclamacao trabalhista e verbas rescisorias").area == "Trabalhista"


@pytest.mark.parametrize("dias, esperado", [(-1, "Crítica"), (2, "Crítica"), (4, "Alta"), (10, "Média"), (30, "Baixa")])
def test_prioridade_pelo_prazo(dias, esperado):
    assert sugerir_prioridade("texto neutro", HOJE + timedelta(days=dias), HOJE).prioridade == esperado


def test_termo_critico_eleva_prioridade():
    r = sugerir_prioridade("Decisão liminar determinou bloqueio judicial", HOJE + timedelta(days=30), HOJE)
    assert r.prioridade == "Crítica"
    assert any("liminar" in m for m in r.motivos)


def test_sem_prazo_fica_media_e_a_definir():
    r = sugerir_prioridade("pedido de parecer", None, HOJE)
    assert (r.prioridade, r.prazo_a_definir) == ("Média", True)
