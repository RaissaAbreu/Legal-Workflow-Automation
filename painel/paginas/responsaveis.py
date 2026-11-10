"""Página: Responsáveis por área (cadastro editável)."""

from __future__ import annotations

from html import escape

import streamlit as st

from legalflow import banco, seed
from legalflow.constantes import AREAS
from painel import componentes as c
from painel import estilo


def _mascarar(url: str) -> str:
    if not url:
        return "Usa o canal padrão (TEAMS_WEBHOOK_PADRAO)"
    return url[:38] + "…" if len(url) > 40 else url


def renderizar() -> None:
    estilo.cabecalho(c.EYEBROW_PADRAO, "Responsáveis",
                     "Quem recebe as demandas de cada área e em qual canal do Microsoft Teams é avisado.")

    estilo.secao("Cadastro / 05", "Equipe jurídica",
                 "Novas demandas vão para o responsável ativo da área com menos demandas em aberto. "
                 "Sem responsável na área, a demanda fica em triagem.")
    responsaveis = banco.listar_responsaveis()

    cobertura = {area: sum(1 for r in responsaveis if r["area"] == area and r["ativo"]) for area in AREAS}
    estilo.metricas([(area, n, n == 0) for area, n in cobertura.items()])

    if not responsaveis:
        st.info("Nenhum responsável cadastrado.")
        if st.button("Carregar responsáveis de exemplo"):
            seed.carregar_responsaveis()
            st.rerun()

    for r in responsaveis:
        with st.container(border=True, key=f"cartao-resp-{r['id']}"):
            estilo.html(f"""<div class="lf-item-cab"><div class="lf-item-titulo">{escape(r['nome'])}</div>
              <div>{estilo.badge(r['area'], 'azul')}{estilo.badge('Ativo' if r['ativo'] else 'Inativo', 'verde' if r['ativo'] else 'neutro')}
              {estilo.badge(f"{r['demandas_abertas']} em aberto", 'neutro')}</div></div>
              <div class="lf-item-meta">{escape(r['email'] or 'sem e-mail')} · Teams: {escape(_mascarar(r['teams_webhook']))}</div>""")
            with st.expander("Editar"):
                with st.form(f"form-resp-{r['id']}", border=False):
                    col1, col2 = st.columns(2)
                    nome = col1.text_input("Nome", value=r["nome"])
                    email = col2.text_input("E-mail", value=r["email"])
                    col3, col4 = st.columns([0.35, 0.65])
                    area = col3.selectbox("Área", AREAS, index=AREAS.index(r["area"]) if r["area"] in AREAS else 0)
                    webhook = col4.text_input("Webhook do Teams", value=r["teams_webhook"], type="password",
                                              help="URL do fluxo “Quando uma solicitação de webhook é recebida” do canal no Teams.")
                    ativo = st.checkbox("Ativo", value=bool(r["ativo"]))
                    b1, b2, _ = st.columns([0.2, 0.2, 0.6])
                    salvar = b1.form_submit_button("Salvar", type="primary")
                    excluir = b2.form_submit_button("Excluir")
                if salvar:
                    if not nome.strip():
                        st.error("Informe o nome.")
                    else:
                        banco.atualizar_responsavel(r["id"], nome=nome.strip(), email=email.strip(), area=area,
                                                    teams_webhook=webhook.strip(), ativo=ativo)
                        st.rerun()
                if excluir:
                    banco.excluir_responsavel(r["id"])
                    st.rerun()

    st.write("")
    with st.container(border=True, key="cartao-resp-novo"):
        estilo.titulo_cartao(None, "Adicionar responsável")
        with st.form("form-resp-novo", clear_on_submit=True, border=False):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome")
            email = col2.text_input("E-mail")
            col3, col4 = st.columns([0.35, 0.65])
            area = col3.selectbox("Área", AREAS)
            webhook = col4.text_input("Webhook do Teams (opcional)", type="password")
            if st.form_submit_button("Adicionar", type="primary"):
                if not nome.strip():
                    st.error("Informe o nome.")
                else:
                    banco.inserir_responsavel(nome, email, area, webhook)
                    st.rerun()
