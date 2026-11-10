"""Página: Prazos e alertas (monitoramento de pendências)."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from legalflow import banco, config, servico
from legalflow.constantes import STATUS_FINAIS, TIPOS_NOTIFICACAO
from painel import componentes as c
from painel import estilo

GRUPOS = [
    ("vencida", "Prazos vencidos", "Demandas em aberto cujo prazo já passou. O alerta se repete a cada 24 horas."),
    ("vence_hoje", "Vencem hoje", "Último dia para cumprir o prazo."),
    ("vence_em_breve", "Vencem nos próximos dias", "Prazo dentro da janela de alerta configurada."),
    ("prazo_a_definir", "Prazo a definir", "Demandas sem data — defina o prazo na triagem."),
]


def renderizar() -> None:
    estilo.cabecalho(c.EYEBROW_PADRAO, "Prazos e alertas",
                     "Monitoramento de prazos e pendências. O n8n consulta esta lista de hora em hora e avisa no Teams.")

    abertas = [d for d in banco.listar_demandas() if d["status"] not in STATUS_FINAIS]
    por_situacao: dict[str, list[dict]] = {}
    for d in abertas:
        por_situacao.setdefault(servico.situacao_prazo(d), []).append(d)
    for lista in por_situacao.values():
        lista.sort(key=lambda d: d["prazo"] or "9999")

    estilo.secao("Monitoramento / 04", "Situação dos prazos",
                 f"Janela de alerta: {config.dias_alerta_proximo()} dia(s) antes do vencimento.")
    estilo.metricas([
        ("Vencidos", len(por_situacao.get("vencida", [])), True),
        ("Vencem hoje", len(por_situacao.get("vence_hoje", [])), True),
        (f"Próximos {config.dias_alerta_proximo()} dias", len(por_situacao.get("vence_em_breve", [])), False),
        ("Prazo a definir", len(por_situacao.get("prazo_a_definir", [])), False),
    ])

    algum = False
    for chave, titulo, texto in GRUPOS:
        demandas = por_situacao.get(chave, [])
        if not demandas:
            continue
        algum = True
        estilo.html(f'<div class="lf-secao-titulo" style="font-size:30px">{escape(titulo)} '
                    f'<span class="lf-muted" style="font-family:inherit;font-size:16px">({len(demandas)})</span></div>'
                    f'<div class="lf-secao-texto lf-muted">{escape(texto)}</div>')
        for demanda in demandas:
            c.item_demanda(demanda, f"prazo-{chave}")
    if not algum:
        st.success("Nenhuma pendência de prazo nas demandas em aberto.")

    st.write("")
    estilo.secao("Monitoramento / 05", "Próxima verificação do n8n",
                 "Alertas que ainda não foram enviados e que o fluxo “Monitor de prazos” enviará na próxima execução.")
    pendentes = servico.alertas_pendentes()
    with st.container(border=True, key="cartao-pendentes"):
        if not pendentes:
            estilo.html('<div class="lf-muted">Nenhum alerta pendente de envio.</div>')
        else:
            itens = "".join(
                f'<li><span class="n">{i}</span><div><div>{escape(a["codigo"])} · {escape(a["tipo_descricao"])}</div>'
                f'<div class="det">Para: {escape(a["destinatario"])}</div></div>'
                f'<span class="dir">{estilo.badge("Canal configurado", "verde") if a["webhook_url"] else estilo.badge("Sem canal do Teams", "ambar")}</span></li>'
                for i, a in enumerate(pendentes, start=1)
            )
            estilo.html(f'<ul class="lf-arquivos">{itens}</ul>')

    st.write("")
    estilo.secao("Monitoramento / 06", "Alertas registrados", "Notificações enviadas (ou tentadas) pelo n8n.")
    notificacoes = banco.listar_notificacoes()
    if not notificacoes:
        st.caption("Nenhuma notificação registrada ainda.")
        return
    situacao = {"enviada": "Enviada", "sem_canal": "Sem canal configurado", "falha": "Falha no envio"}
    st.dataframe(pd.DataFrame([{
        "Quando": c.data_hora(n["criado_em"]),
        "Demanda": n["codigo"],
        "Assunto": n["assunto"],
        "Tipo": TIPOS_NOTIFICACAO.get(n["tipo"], n["tipo"]),
        "Situação": situacao.get(n["situacao"], n["situacao"]),
    } for n in notificacoes]), hide_index=True, use_container_width=True)
