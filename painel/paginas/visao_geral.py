"""Página: Visão geral (indicadores e demandas que exigem atenção)."""

from __future__ import annotations

import streamlit as st

from legalflow import banco, seed, servico
from legalflow.constantes import AREA_NAO_CLASSIFICADA, AREAS, PRIORIDADES, STATUS_FINAIS
from painel import componentes as c
from painel import estilo

ORDEM_URGENCIA = {"vencida": 0, "vence_hoje": 1, "vence_em_breve": 2, "prazo_a_definir": 3, "no_prazo": 4}


def renderizar() -> None:
    estilo.cabecalho(c.EYEBROW_PADRAO, "Visão geral",
                     "Acompanhe as demandas jurídicas recebidas, os prazos e os encaminhamentos.",
                     selo="Modo demonstração")

    demandas = banco.listar_demandas()
    if not demandas:
        with st.container(border=True, key="cartao-vazio"):
            estilo.titulo_cartao(None, "Nenhuma demanda registrada ainda")
            estilo.html('<div class="lf-muted">Registre uma demanda em “Nova demanda”, envie uma pelo webhook do n8n '
                        "ou carregue o conjunto de demandas fictícias de demonstração.</div>")
            st.write("")
            if st.button("Carregar demandas de exemplo", type="primary", help="10 demandas e 5 responsáveis fictícios."):
                seed.carregar_demandas()
                st.rerun()
        return

    ind = servico.indicadores()
    estilo.secao("Painel / 01", "Indicadores", "Demandas em aberto e situação dos prazos, atualizadas a cada consulta.")
    estilo.metricas([
        ("Em aberto", ind["abertas"], False),
        ("Prazos vencidos", ind["vencidas"], True),
        ("Vencem em até 3 dias", ind["vencem_breve"], False),
        ("Prazo a definir", ind["prazo_a_definir"], False),
    ])

    abertas = [d for d in demandas if d["status"] not in STATUS_FINAIS]
    col_area, col_prio = st.columns(2, gap="medium")
    with col_area:
        with st.container(border=True, key="cartao-por-area"):
            estilo.titulo_cartao(None, "Demandas em aberto por área")
            contagem = c.contagem_por(abertas, "area", AREAS + [AREA_NAO_CLASSIFICADA])
            estilo.barras(contagem)
    with col_prio:
        with st.container(border=True, key="cartao-por-prioridade"):
            estilo.titulo_cartao(None, "Demandas em aberto por prioridade")
            estilo.barras(c.contagem_por(abertas, "prioridade", list(reversed(PRIORIDADES))))
            estilo.html(f'<div class="lf-muted" style="margin-top:14px">{ind["em_triagem"]} aguardando triagem · '
                        f'{ind["concluidas"]} concluída(s) no total</div>')

    st.write("")
    estilo.secao("Painel / 02", "Atenção imediata",
                 "Demandas em aberto ordenadas pela urgência do prazo e pela prioridade.")
    ordenadas = sorted(
        abertas,
        key=lambda d: (ORDEM_URGENCIA.get(servico.situacao_prazo(d), 9),
                       -PRIORIDADES.index(d["prioridade"]), d["prazo"] or "9999"),
    )
    for demanda in ordenadas[:5]:
        c.item_demanda(demanda, "visao")
    if len(ordenadas) > 5:
        st.button(f"Ver todas as {len(ordenadas)} demandas em aberto", on_click=c.ir_para, args=("Demandas e triagem",))
