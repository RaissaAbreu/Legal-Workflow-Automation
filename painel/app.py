"""Painel de acompanhamento — LEGAL FLOW.

Executar a partir da raiz do projeto:  streamlit run painel/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from legalflow import VERSAO, banco, config  # noqa: E402
from legalflow.classificacao import MOTOR  # noqa: E402
from painel import componentes as c  # noqa: E402
from painel import estilo  # noqa: E402
from painel.paginas import como_funciona, demandas, nova_demanda, prazos, responsaveis, visao_geral  # noqa: E402

st.set_page_config(page_title="Legal Flow", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")
estilo.aplicar()
banco.inicializar()

# Link vindo do Teams: ?demanda=DEM-0001 abre direto o detalhe.
if (codigo := st.query_params.get("demanda")) and not st.session_state.get("link_consumido"):
    st.session_state["link_consumido"] = True
    c.ir_para("Demandas e triagem", codigo.upper())

ROTAS = {
    "Visão geral": visao_geral.renderizar,
    "Nova demanda": nova_demanda.renderizar,
    "Demandas e triagem": demandas.renderizar,
    "Prazos e alertas": prazos.renderizar,
    "Responsáveis": responsaveis.renderizar,
    "Como funciona": como_funciona.renderizar,
}

with st.sidebar:
    estilo.html('<div class="lf-marca"><div class="nome">LEGAL FLOW</div>'
                '<div class="sub">AUTOMAÇÃO DE DEMANDAS<br>JURÍDICAS</div></div>')
    estilo.html('<div class="lf-rotulo-lateral">Área de trabalho</div>')
    st.radio("Navegação", c.PAGINAS, key="pagina", label_visibility="collapsed")

    estilo.html('<div class="lf-sep"></div><div class="lf-rotulo-lateral">Motor de classificação</div>')
    st.selectbox("Provedor", [MOTOR], disabled=True)
    estilo.html('<div class="lf-nota-lateral"><span class="ponto"></span>Classificação por regras, sem envio de dados</div>')

    n8n_ok = bool(config.url_webhook_n8n())
    teams_ok = bool(config.teams_webhook_padrao()) or any(r["teams_webhook"] for r in banco.listar_responsaveis(True))
    estilo.html(f"""<div class="lf-sep"></div><div class="lf-rotulo-lateral">Integrações</div>
      <div class="lf-nota-lateral"><span class="ponto {'ok' if n8n_ok else 'off'}"></span>n8n: {'webhook configurado' if n8n_ok else 'não configurado'}</div>
      <div class="lf-nota-lateral"><span class="ponto {'ok' if teams_ok else 'off'}"></span>Teams: {'canal configurado' if teams_ok else 'sem canal configurado'}</div>""")

    estilo.html(f"""<div class="lf-sep"></div><div class="lf-rotulo-lateral">Operações jurídicas</div>
      <div class="lf-rodape-lateral"><div class="titulo">Automação do fluxo de demandas jurídicas.</div>
      <div class="meta">Versão {VERSAO} · Use somente dados fictícios ou anonimizados.</div></div>""")

ROTAS[st.session_state.get("pagina", c.PAGINAS[0])]()
