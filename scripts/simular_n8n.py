"""Executa, sem o n8n, os mesmos passos dos dois workflows — útil para testar a API.

    python scripts/simular_n8n.py entrada exemplos/formulario.json   # fluxo "Entrada de demandas"
    python scripts/simular_n8n.py monitor                            # fluxo "Monitor de prazos"

Variável LEGALFLOW_API_URL (padrão http://localhost:8000).
"""

import json
import os
import sys
import urllib.error
import urllib.request

API = os.getenv("LEGALFLOW_API_URL", "http://localhost:8000").rstrip("/")


def requisitar(url, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method="POST" if dados else "GET",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        texto = resp.read().decode() or "{}"
        return json.loads(texto) if texto.strip().startswith(("{", "[")) else {}


def notificar(demanda_id, tipo, webhook_url, payload):
    """Envia ao Teams (se houver canal) e registra o resultado — como os nós do n8n."""
    if webhook_url:
        try:
            requisitar(webhook_url, payload)
            situacao = "enviada"
        except (urllib.error.URLError, TimeoutError):
            situacao = "falha"
    else:
        situacao = "sem_canal"
    requisitar(f"{API}/notificacoes", {"demanda_id": demanda_id, "tipo": tipo, "situacao": situacao,
                                       "destino": "Microsoft Teams"})
    return situacao


def entrada(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        corpo = json.load(arquivo)
    resposta = requisitar(f"{API}/demandas", corpo)
    d, n = resposta["demanda"], resposta["notificacao"]
    situacao = notificar(d["id"], "nova_demanda", n["webhook_url"], n["payload"])
    print(f"{d['codigo']} · {d['area']} · prioridade {d['prioridade']} · {d['status']} · notificação: {situacao}")


def monitor():
    alertas = requisitar(f"{API}/alertas/pendentes")["alertas"]
    for a in alertas:
        print(f"{a['codigo']} · {a['tipo_descricao']} · {notificar(a['demanda_id'], a['tipo'], a['webhook_url'], a['payload'])}")
    print(f"{len(alertas)} alerta(s) processado(s).")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "monitor":
        monitor()
    elif len(sys.argv) >= 3 and sys.argv[1] == "entrada":
        entrada(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
