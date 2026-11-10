"""Dados fictícios de demonstração. Uso: python -m legalflow.seed

Nomes, empresas e processos são inventados. Os prazos são relativos à data de hoje,
para que o painel sempre mostre demandas vencidas, próximas do vencimento e no prazo.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from . import banco, servico
from .extracao import Anexo

RESPONSAVEIS = [
    ("Marina Duarte", "marina.duarte@exemplo.com.br", "Trabalhista"),
    ("Rafael Nogueira", "rafael.nogueira@exemplo.com.br", "Cível"),
    ("Camila Prado", "camila.prado@exemplo.com.br", "Consumidor"),
    ("Thiago Albuquerque", "thiago.albuquerque@exemplo.com.br", "Contratual"),
    ("Beatriz Lemos", "beatriz.lemos@exemplo.com.br", "Regulatória"),
]


def _d(dias: int) -> str:
    return (date.today() + timedelta(days=dias)).strftime("%d/%m/%Y")


def _demandas() -> list[dict]:
    return [
        dict(canal="E-mail", solicitante="Paulo Henrique Matos", departamento="Recursos Humanos",
             assunto="Reclamação trabalhista — ex-colaborador do centro de distribuição",
             descricao=("Recebemos notificação da Vara do Trabalho sobre reclamação trabalhista de ex-funcionário "
                        "pedindo horas extras e verbas rescisórias. Audiência inicial marcada; prazo para "
                        f"apresentar documentos até {_d(2)}. Seguem cartões de ponto e TRCT."),
             horas=30, docs=[("cartoes_ponto_resumo.txt", "Resumo fictício de cartões de ponto — 2025.")]),
        dict(canal="Formulário", solicitante="Juliana Castro", departamento="Atendimento ao Cliente",
             assunto="Notificação Procon — cobrança indevida em fatura",
             descricao=("Cliente registrou reclamação no Procon alegando cobrança indevida e pedindo reembolso "
                        f"em dobro com base no CDC. Prazo de resposta ao Procon até {_d(-1)}."),
             horas=96),
        dict(canal="Formulário", solicitante="André Vasconcelos", departamento="Compras",
             assunto="Revisão de minuta — contrato de prestação de serviços de TI",
             descricao=("Precisamos da revisão da minuta do contrato de prestação de serviços com novo fornecedor, "
                        "com atenção à cláusula de SLA, multa contratual e renovação automática. "
                        f"Assinatura prevista; prazo até {_d(12)}."),
             horas=6, docs=[("minuta_contrato_ti.txt", "CLÁUSULA 5 — SLA de 99,5%. CLÁUSULA 9 — Multa contratual de 10%.")]),
        dict(canal="E-mail", solicitante="Fernanda Ribeiro", departamento="Segurança da Informação",
             assunto="Incidente de segurança — possível vazamento de dados pessoais",
             descricao=("Identificamos incidente de segurança com possível vazamento de dados pessoais de clientes. "
                        "Avaliar comunicação à ANPD conforme LGPD em 48 horas."),
             horas=3),
        dict(canal="Formulário", solicitante="Ricardo Menezes", departamento="Financeiro",
             assunto="Liminar com bloqueio judicial de contas",
             descricao=("Fomos intimados de decisão liminar em ação de cobrança na vara cível determinando bloqueio "
                        f"judicial de valores. Prazo para manifestação até {_d(1)}."),
             horas=2),
        dict(canal="E-mail", solicitante="Luciana Farias", departamento="Marketing",
             assunto="Acordo de confidencialidade para parceria",
             descricao="Solicito modelo de NDA (acordo de confidencialidade) para parceria com agência de eventos.",
             horas=50),
        dict(canal="Formulário", solicitante="Gustavo Almeida", departamento="Operações",
             assunto="Ofício da ANVISA sobre rotulagem",
             descricao=("Recebemos ofício da ANVISA (agência reguladora) solicitando esclarecimentos sobre rotulagem. "
                        f"Prazo de 20 dias corridos — vencimento em {_d(20)}."),
             horas=20),
        dict(canal="E-mail", solicitante="Patrícia Gomes", departamento="Facilities",
             assunto="Ação de despejo — imóvel da filial Centro",
             descricao=("Locador ajuizou ação de despejo por suposto atraso de aluguel da filial. Recebemos a citação; "
                        f"prazo para contestação até {_d(4)}."),
             horas=12),
        dict(canal="Formulário", solicitante="Eduardo Lima", departamento="Diretoria",
             assunto="Dúvida sobre procedimento interno",
             descricao="Gostaria de entender qual o melhor procedimento para aprovar a nova política interna de viagens.",
             horas=40),
        dict(canal="Formulário", solicitante="Sônia Barbosa", departamento="Atendimento ao Cliente",
             assunto="Reclame Aqui — produto com defeito",
             descricao=("Consumidor relata produto com defeito e pede troca no Reclame Aqui. Já providenciamos a "
                        f"devolução. Responder até {_d(-5)}."),
             horas=200, concluir=True),
    ]


def carregar_responsaveis() -> int:
    banco.inicializar()
    existentes = {r["email"] for r in banco.listar_responsaveis()}
    novos = 0
    for nome, email, area in RESPONSAVEIS:
        if email not in existentes:
            banco.inserir_responsavel(nome, email, area)
            novos += 1
    return novos


def carregar_demandas() -> int:
    banco.inicializar()
    carregar_responsaveis()
    agora = datetime.now()
    for item in _demandas():
        demanda = servico.registrar_demanda(servico.EntradaDemanda(
            canal=item["canal"], solicitante=item["solicitante"], departamento=item["departamento"],
            assunto=item["assunto"], descricao=item["descricao"],
            documentos=[Anexo(n, c.encode("utf-8")) for n, c in item.get("docs", [])],
            recebida_em=agora - timedelta(hours=item["horas"]),
        ))
        if item.get("concluir"):
            servico.atualizar_triagem(demanda["id"], {"status": "Concluída",
                                                      "observacoes": "Resposta enviada ao consumidor."},
                                      autor="Demonstração")
    return len(_demandas())


if __name__ == "__main__":
    print(f"{carregar_responsaveis()} responsável(is) e {carregar_demandas()} demanda(s) de exemplo carregados.")
