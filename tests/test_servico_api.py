import base64
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from legalflow import banco, servico
from legalflow.api import app
from legalflow.config import RAIZ_PROJETO
from legalflow.extracao import Anexo

cliente = TestClient(app)


def _responsavel(area="Consumidor", webhook=""):
    return banco.inserir_responsavel("Pessoa Teste", "p@exemplo.com", area, webhook)


def test_registra_e_encaminha_para_responsavel_da_area():
    rid = _responsavel()
    d = servico.registrar_demanda(servico.EntradaDemanda(
        assunto="Procon", descricao="Reclamação no Procon por cobrança indevida, prazo até 20/12/2030",
        documentos=[Anexo("nota.txt", b"consumidor pede reembolso")]))
    assert d["area"] == "Consumidor" and d["status"] == "Encaminhada" and d["responsavel_id"] == rid
    assert d["prazo"] == "2030-12-20" and d["qtd_documentos"] == 1
    assert [h["evento"] for h in banco.listar_historico(d["id"])] == ["Encaminhada", "Classificada", "Recebida"]


def test_sem_responsavel_vai_para_triagem():
    d = servico.registrar_demanda(servico.EntradaDemanda(descricao="Reclamação trabalhista com horas extras"))
    assert d["status"] == "Em triagem" and d["responsavel_id"] is None


def test_balanceia_entre_responsaveis():
    a = _responsavel()
    b = _responsavel()
    ids = [servico.registrar_demanda(servico.EntradaDemanda(descricao="Procon e consumidor"))["responsavel_id"]
           for _ in range(2)]
    assert sorted(ids) == sorted([a, b])


def test_triagem_registra_historico_e_conclusao():
    d = servico.registrar_demanda(servico.EntradaDemanda(descricao="pedido genérico"))
    mudancas = servico.atualizar_triagem(d["id"], {"area": "Cível", "status": "Concluída", "prazo": date(2030, 1, 2)}, "Ana")
    atual = banco.obter_demanda(d["id"])
    assert atual["area"] == "Cível" and atual["concluida_em"] and not atual["prazo_a_definir"]
    assert len(mudancas) == 3


def test_api_cria_demanda_por_email_e_devolve_notificacao():
    _responsavel(webhook="https://teams.exemplo/webhook")
    eml = (RAIZ_PROJETO / "exemplos" / "email_notificacao_procon.eml").read_bytes()
    r = cliente.post("/demandas", json={"email_eml_base64": base64.b64encode(eml).decode()})
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["demanda"]["canal"] == "E-mail"
    assert corpo["demanda"]["area"] == "Consumidor"
    assert corpo["demanda"]["solicitante"] == "Renata Oliveira"
    assert corpo["notificacao"]["webhook_url"] == "https://teams.exemplo/webhook"
    cartao = corpo["notificacao"]["payload"]["attachments"][0]
    assert cartao["contentType"] == "application/vnd.microsoft.card.adaptive"


def test_api_valida_entrada_vazia_e_base64():
    assert cliente.post("/demandas", json={}).status_code == 422
    r = cliente.post("/demandas", json={"assunto": "x", "documentos": [{"nome": "a.txt", "conteudo_base64": "@@"}]})
    assert r.status_code == 422


def test_alertas_e_deduplicacao():
    hoje = date.today()
    vencida = servico.registrar_demanda(servico.EntradaDemanda(descricao="contrato", prazo=hoje - timedelta(days=1)))
    breve = servico.registrar_demanda(servico.EntradaDemanda(descricao="contrato", prazo=hoje + timedelta(days=2)))
    servico.registrar_demanda(servico.EntradaDemanda(descricao="contrato", prazo=hoje + timedelta(days=30)))

    tipos = {a["codigo"]: a["tipo"] for a in cliente.get("/alertas/pendentes").json()["alertas"]}
    assert tipos == {vencida["codigo"]: "vencida", breve["codigo"]: "vence_em_breve"}

    for codigo, tipo in tipos.items():
        demanda = banco.obter_demanda_por_codigo(codigo)
        assert cliente.post("/notificacoes", json={"demanda_id": demanda["id"], "tipo": tipo,
                                                   "situacao": "sem_canal"}).status_code == 201
    assert servico.alertas_pendentes() == []
    # o alerta de prazo vencido volta depois de 24 horas
    assert [a["tipo"] for a in servico.alertas_pendentes(datetime.now() + timedelta(hours=25))] == ["vencida"]


def test_prazo_a_definir_alerta_apos_24h():
    d = servico.registrar_demanda(servico.EntradaDemanda(descricao="parecer",
                                                        recebida_em=datetime.now() - timedelta(hours=30)))
    assert [(a["codigo"], a["tipo"]) for a in servico.alertas_pendentes()] == [(d["codigo"], "prazo_a_definir")]


def test_seed_carrega_dados():
    from legalflow import seed

    assert seed.carregar_demandas() == 10
    assert servico.indicadores()["total"] == 10
