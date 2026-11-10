"""Listas de domínio usadas em todo o sistema."""

AREAS = ["Trabalhista", "Cível", "Consumidor", "Contratual", "Regulatória"]
AREA_NAO_CLASSIFICADA = "Não classificada"
AREAS_COM_INDEFINIDA = AREAS + [AREA_NAO_CLASSIFICADA]

PRIORIDADES = ["Baixa", "Média", "Alta", "Crítica"]  # ordem crescente

STATUS = [
    "Nova",
    "Em triagem",
    "Encaminhada",
    "Em andamento",
    "Aguardando terceiros",
    "Concluída",
    "Cancelada",
]
STATUS_FINAIS = {"Concluída", "Cancelada"}

CANAIS = ["Formulário", "E-mail", "Painel"]

TIPOS_NOTIFICACAO = {
    "nova_demanda": "Nova demanda",
    "vencida": "Prazo vencido",
    "vence_hoje": "Vence hoje",
    "vence_em_breve": "Vence em breve",
    "prazo_a_definir": "Prazo a definir",
}

SITUACOES_NOTIFICACAO = ["enviada", "sem_canal", "falha"]

# Confiança mínima para encaminhar automaticamente; abaixo disso a demanda vai para triagem.
CONFIANCA_MINIMA_ENCAMINHAMENTO = 0.5
