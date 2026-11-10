"""Gera os workflows do n8n (n8n/workflows/*.json).

Os JSON gerados já estão no repositório; rode este script só se quiser alterar os fluxos por código:
    python scripts/gerar_workflows_n8n.py
"""

import json
import uuid
from pathlib import Path

API = "http://api:8000"  # nome do serviço no docker-compose
DESTINO = Path(__file__).resolve().parent.parent / "n8n" / "workflows"


def no(nome, tipo, versao, posicao, parametros, **extra):
    return {"parameters": parametros, "name": nome, "type": tipo, "typeVersion": versao,
            "position": posicao, "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"legalflow/{nome}")), **extra}


def http_json(nome, posicao, url, corpo, metodo="POST", **extra):
    return no(nome, "n8n-nodes-base.httpRequest", 4.2, posicao, {
        "method": metodo, "url": url, "sendBody": True, "specifyBody": "json",
        "jsonBody": corpo, "options": {"timeout": 30000},
    }, **extra)


def se_nao_vazio(nome, posicao, expressao):
    return no(nome, "n8n-nodes-base.if", 2, posicao, {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
            "conditions": [{"id": "canal-teams", "leftValue": expressao, "rightValue": "",
                            "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}}],
            "combinator": "and",
        },
        "options": {},
    })


def liga(*destinos):
    return [[{"node": d, "type": "main", "index": 0}] for d in destinos]


def registrar(nome, posicao, demanda_id, tipo, situacao):
    corpo = ("={{ JSON.stringify({ demanda_id: " + demanda_id + ", tipo: " + tipo
             + ", situacao: " + situacao + ", destino: 'Microsoft Teams' }) }}")
    return http_json(nome, posicao, f"{API}/notificacoes", corpo)


def entrada():
    reg = "Registrar demanda (API)"
    nos = [
        no("Webhook nova demanda", "n8n-nodes-base.webhook", 2, [0, 300],
           {"httpMethod": "POST", "path": "nova-demanda", "responseMode": "responseNode", "options": {}},
           webhookId="legalflow-nova-demanda"),
        http_json(reg, [240, 300], f"{API}/demandas", "={{ JSON.stringify($json.body) }}",
                  onError="continueErrorOutput"),
        se_nao_vazio("Tem canal do Teams?", [500, 200], "={{ $json.notificacao.webhook_url }}"),
        http_json("Notificar responsável no Teams", [760, 100], "={{ $json.notificacao.webhook_url }}",
                  "={{ JSON.stringify($json.notificacao.payload) }}", onError="continueRegularOutput"),
        registrar("Registrar envio", [1000, 100], f"$('{reg}').item.json.demanda.id", "'nova_demanda'",
                  "($json.error ? 'falha' : 'enviada')"),
        registrar("Registrar sem canal", [760, 320], f"$('{reg}').item.json.demanda.id", "'nova_demanda'",
                  "'sem_canal'"),
        no("Responder", "n8n-nodes-base.respondToWebhook", 1.1, [1240, 200],
           {"respondWith": "json", "responseBody": f"={{{{ JSON.stringify($('{reg}').item.json) }}}}",
            "options": {"responseCode": 201}}),
        no("Responder erro", "n8n-nodes-base.respondToWebhook", 1.1, [500, 460],
           {"respondWith": "json",
            "responseBody": "={{ JSON.stringify({ erro: 'Não foi possível registrar a demanda', detalhe: $json.error }) }}",
            "options": {"responseCode": 422}}),
    ]
    conexoes = {
        "Webhook nova demanda": {"main": liga(reg)},
        reg: {"main": [[{"node": "Tem canal do Teams?", "type": "main", "index": 0}],
                       [{"node": "Responder erro", "type": "main", "index": 0}]]},
        "Tem canal do Teams?": {"main": [[{"node": "Notificar responsável no Teams", "type": "main", "index": 0}],
                                         [{"node": "Registrar sem canal", "type": "main", "index": 0}]]},
        "Notificar responsável no Teams": {"main": liga("Registrar envio")},
        "Registrar envio": {"main": liga("Responder")},
        "Registrar sem canal": {"main": liga("Responder")},
    }
    return {"id": "LegalFlowEntrada01", "name": "LEGAL FLOW — Entrada de demandas", "nodes": nos,
            "connections": conexoes, "active": False, "settings": {"executionOrder": "v1"}, "pinData": {}}


def monitor():
    sep = "Separar alertas"
    nos = [
        no("A cada hora", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 200],
           {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}}),
        no("Executar agora (teste)", "n8n-nodes-base.manualTrigger", 1, [0, 400], {}),
        no("Buscar alertas pendentes", "n8n-nodes-base.httpRequest", 4.2, [240, 300],
           {"method": "GET", "url": f"{API}/alertas/pendentes", "options": {"timeout": 30000}}),
        no(sep, "n8n-nodes-base.splitOut", 1, [480, 300], {"fieldToSplitOut": "alertas", "options": {}}),
        se_nao_vazio("Tem canal do Teams?", [720, 300], "={{ $json.webhook_url }}"),
        http_json("Enviar alerta ao Teams", [960, 200], "={{ $json.webhook_url }}",
                  "={{ JSON.stringify($json.payload) }}", onError="continueRegularOutput"),
        registrar("Registrar envio", [1200, 200], f"$('{sep}').item.json.demanda_id",
                  f"$('{sep}').item.json.tipo", "($json.error ? 'falha' : 'enviada')"),
        registrar("Registrar sem canal", [960, 420], "$json.demanda_id", "$json.tipo", "'sem_canal'"),
    ]
    conexoes = {
        "A cada hora": {"main": liga("Buscar alertas pendentes")},
        "Executar agora (teste)": {"main": liga("Buscar alertas pendentes")},
        "Buscar alertas pendentes": {"main": liga(sep)},
        sep: {"main": liga("Tem canal do Teams?")},
        "Tem canal do Teams?": {"main": [[{"node": "Enviar alerta ao Teams", "type": "main", "index": 0}],
                                         [{"node": "Registrar sem canal", "type": "main", "index": 0}]]},
        "Enviar alerta ao Teams": {"main": liga("Registrar envio")},
    }
    return {"id": "LegalFlowMonitor01", "name": "LEGAL FLOW — Monitor de prazos", "nodes": nos,
            "connections": conexoes, "active": False, "settings": {"executionOrder": "v1"}, "pinData": {}}


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    for nome, fluxo in (("01_entrada_demandas.json", entrada()), ("02_monitor_prazos.json", monitor())):
        (DESTINO / nome).write_text(json.dumps(fluxo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("gerado:", DESTINO / nome)
