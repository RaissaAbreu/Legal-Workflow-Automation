"""Página: Demandas e triagem (lista, detalhe e correção da classificação)."""

from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from legalflow import banco, servico
from legalflow.classificacao import TERMOS_POR_AREA
from legalflow.constantes import AREAS_COM_INDEFINIDA, PRIORIDADES, STATUS, STATUS_FINAIS, TIPOS_NOTIFICACAO
from legalflow.texto import normalizar
from painel import componentes as c
from painel import estilo


def _filtrar(demandas: list[dict]) -> list[dict]:
    with st.container(border=True, key="cartao-filtros"):
        col1, col2, col3, col4 = st.columns([0.34, 0.22, 0.22, 0.22])
        busca = col1.text_input("Buscar", placeholder="Código, assunto ou solicitante", key="f_busca")
        areas = col2.multiselect("Área", AREAS_COM_INDEFINIDA, key="f_area", placeholder="Todas")
        prioridades = col3.multiselect("Prioridade", list(reversed(PRIORIDADES)), key="f_prio", placeholder="Todas")
        status = col4.multiselect("Status", STATUS, key="f_status", placeholder="Todos")
        incluir_encerradas = st.checkbox("Mostrar também demandas concluídas e canceladas", key="f_encerradas")

    termo = normalizar(busca)
    resultado = []
    for d in demandas:
        if not incluir_encerradas and not status and d["status"] in STATUS_FINAIS:
            continue
        if termo and termo not in normalizar(f"{d['codigo']} {d['assunto']} {d['solicitante']} {d['departamento']}"):
            continue
        if areas and d["area"] not in areas:
            continue
        if prioridades and d["prioridade"] not in prioridades:
            continue
        if status and d["status"] not in status:
            continue
        resultado.append(d)
    return resultado


def _tabela(demandas: list[dict]) -> None:
    linhas = [{
        "Código": d["codigo"],
        "Assunto": d["assunto"],
        "Área": d["area"],
        "Prioridade": d["prioridade"],
        "Prazo": c.texto_prazo(d),
        "Status": d["status"],
        "Responsável": d.get("responsavel_nome") or "—",
        "Recebida em": c.data_hora(d["recebida_em"]),
    } for d in demandas]
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True,
                 height=min(38 + 35 * len(linhas), 330))


def _aba_resumo(demanda: dict) -> None:
    with st.container(border=True, key="cartao-aba-resumo"):
        estilo.titulo_cartao(None, "Descrição da demanda")
        texto = escape(demanda["descricao"] or "(sem descrição)").replace("\n", "<br>")
        estilo.html(f'<div style="font-size:15.5px;line-height:1.65">{texto}</div>')
        estilo.html('<div class="lf-rotulo">Por que esta prioridade</div><ul class="lf-lista">'
                    + "".join(f"<li>{escape(m)}</li>" for m in demanda["motivos"] or []) + "</ul>")
        if demanda["observacoes"]:
            estilo.html('<div class="lf-rotulo">Observações do analista</div>'
                        f'<div>{escape(demanda["observacoes"])}</div>')


def _aba_classificacao(demanda: dict) -> None:
    with st.container(border=True, key="cartao-aba-classificacao"):
        estilo.titulo_cartao(None, "Pontuação por área")
        estilo.html(f'<div class="lf-muted" style="margin-bottom:14px">Motor: {escape(demanda["motor"])}. '
                    "Cada termo encontrado soma o seu peso (1 a 3); a área com mais pontos é sugerida.</div>")
        estilo.barras({area: (demanda["pontuacoes"] or {}).get(area, 0) for area in TERMOS_POR_AREA})
        estilo.html('<div class="lf-rotulo">Termos encontrados por área</div>')
        termos = demanda["termos"] or {}
        if not termos:
            estilo.html('<div class="lf-muted">Nenhum termo característico encontrado — a demanda precisa de triagem manual.</div>')
        for area, lista in termos.items():
            estilo.html(f'<div style="margin:6px 0"><b>{escape(area)}:</b> '
                        + "".join(estilo.badge(t, "azul" if area == demanda["area"] else "neutro") for t in lista) + "</div>")


def _aba_documentos(demanda: dict, documentos: list[dict]) -> None:
    with st.container(border=True, key="cartao-aba-documentos"):
        estilo.titulo_cartao(None, "Documentos da demanda")
        if not documentos:
            estilo.html('<div class="lf-muted">Nenhum documento anexado.</div>')
        for i, doc in enumerate(documentos, start=1):
            col_info, col_botao = st.columns([0.75, 0.25])
            leitura = (f"{doc['caracteres_texto']} caracteres de texto lidos" if doc["caracteres_texto"]
                       else "sem texto extraído (imagem ou formato não lido)")
            col_info.markdown(f'<ul class="lf-arquivos"><li><span class="n">{i}</span><div><div>{escape(doc["nome"])}</div>'
                              f'<div class="det">{doc["tamanho"] / 1024:.1f} KB · {leitura}</div></div></li></ul>',
                              unsafe_allow_html=True)
            caminho = Path(doc["caminho"])
            if caminho.exists():
                col_botao.download_button("Baixar", caminho.read_bytes(), file_name=doc["nome"],
                                          key=f"baixar-doc-{doc['id']}", use_container_width=True)
            else:
                col_botao.caption("Arquivo indisponível")


def _aba_triagem(demanda: dict) -> None:
    sugestao = (f"Área {demanda['area_sugerida']} (confiança {demanda['confianca']:.0%}) "
                f"com prioridade {demanda['prioridade_sugerida'].lower()}.")
    with st.container(border=True, key="cartao-aba-triagem"):
        estilo.recomendacao("Sugestão da automação", sugestao)
        estilo.html('<div class="lf-muted" style="margin-bottom:12px">A classificação é preliminar e precisa de validação humana. '
                    "Toda alteração fica registrada no histórico.</div>")
        with st.form(f"form-triagem-{demanda['id']}", border=False):
            col1, col2, col3 = st.columns(3)
            area = col1.selectbox("Área jurídica", AREAS_COM_INDEFINIDA, index=AREAS_COM_INDEFINIDA.index(demanda["area"]))
            prioridade = col2.selectbox("Prioridade", PRIORIDADES, index=PRIORIDADES.index(demanda["prioridade"]))
            status = col3.selectbox("Status", STATUS, index=STATUS.index(demanda["status"]))

            col4, col5 = st.columns([0.4, 0.6])
            prazo_atual = date.fromisoformat(demanda["prazo"]) if demanda["prazo"] else None
            prazo = col4.date_input("Prazo", value=prazo_atual, format="DD/MM/YYYY")
            opcoes = c.opcoes_responsavel(demanda["area"])
            ids = list(opcoes)
            responsavel = col5.selectbox("Responsável", ids, format_func=opcoes.get,
                                         index=ids.index(demanda["responsavel_id"]) if demanda["responsavel_id"] in ids else 0)
            sem_prazo = st.checkbox("Prazo a definir (sem data)", value=demanda["prazo"] is None)
            observacoes = st.text_area("Observações", value=demanda["observacoes"], height=90)
            autor = st.text_input("Analista", value=st.session_state.get("analista", ""), placeholder="Seu nome (opcional)")
            enviado = st.form_submit_button("Registrar triagem", type="primary")

        if enviado:
            st.session_state["analista"] = autor
            alteracoes = {"area": area, "prioridade": prioridade, "status": status,
                          "prazo": None if sem_prazo else prazo, "responsavel_id": responsavel,
                          "observacoes": observacoes.strip()}
            if responsavel and status in ("Nova", "Em triagem") and demanda["status"] in ("Nova", "Em triagem"):
                alteracoes["status"] = "Encaminhada"  # atribuir responsável na triagem já encaminha
            mudancas = servico.atualizar_triagem(demanda["id"], alteracoes, autor=autor.strip() or "Analista")
            st.session_state["triagem_msg"] = mudancas or ["Nenhuma alteração."]
            st.rerun()

        if msg := st.session_state.pop("triagem_msg", None):
            st.success("Triagem registrada: " + "; ".join(msg))


def _aba_historico(demanda: dict) -> None:
    with st.container(border=True, key="cartao-aba-historico"):
        estilo.titulo_cartao(None, "Histórico")
        itens = "".join(
            f'<li><div class="evento">{escape(h["evento"])}</div><div>{escape(h["detalhe"])}</div>'
            f'<div class="quando">{c.data_hora(h["criado_em"])} · {escape(h["autor"])}</div></li>'
            for h in banco.listar_historico(demanda["id"])
        )
        estilo.html(f'<ul class="lf-tempo">{itens}</ul>')


def _aba_notificacoes(demanda: dict, notificacoes: list[dict]) -> None:
    with st.container(border=True, key="cartao-aba-notificacoes"):
        estilo.titulo_cartao(None, "Notificações no Microsoft Teams")
        if not notificacoes:
            estilo.html('<div class="lf-muted">Nenhuma notificação registrada. As notificações são enviadas pelo n8n: '
                        "na entrada da demanda e pelo monitor de prazos (de hora em hora).</div>")
            return
        rotulo = {"enviada": ("Enviada", "verde"), "sem_canal": ("Sem canal configurado", "ambar"), "falha": ("Falha", "vermelho")}
        linhas = "".join(
            f'<li><span class="n">{i}</span><div><div>{escape(TIPOS_NOTIFICACAO.get(n["tipo"], n["tipo"]))}</div>'
            f'<div class="det">{c.data_hora(n["criado_em"])} · {escape(n["canal"])}</div></div>'
            f'<span class="dir">{estilo.badge(*rotulo.get(n["situacao"], (n["situacao"], "neutro")))}</span></li>'
            for i, n in enumerate(notificacoes, start=1)
        )
        estilo.html(f'<ul class="lf-arquivos">{linhas}</ul>')


def renderizar() -> None:
    estilo.cabecalho(c.EYEBROW_PADRAO, "Demandas e triagem",
                     "Consulte a extração automática, confirme a classificação e acompanhe o andamento de cada demanda.")

    todas = banco.listar_demandas()
    if not todas:
        st.info("Nenhuma demanda registrada. Use “Nova demanda” ou carregue os exemplos na “Visão geral”.")
        return

    estilo.secao("Controle / 03", "Central de demandas",
                 "Filtre a lista e selecione uma demanda para ver o detalhe e registrar a triagem.")
    filtradas = _filtrar(todas)
    estilo.metricas([
        ("Na lista", len(filtradas), False),
        ("Em triagem", sum(d["status"] in ("Nova", "Em triagem") for d in filtradas), False),
        ("Prioridade crítica", sum(d["prioridade"] == "Crítica" for d in filtradas), True),
        ("Sem responsável", sum(not d["responsavel_id"] for d in filtradas), False),
    ])
    if not filtradas:
        st.warning("Nenhuma demanda encontrada com esses filtros.")
        return
    _tabela(filtradas)

    st.write("")
    codigos = [d["codigo"] for d in todas]
    rotulos = {d["codigo"]: f"{d['codigo']} — {d['assunto']} · {d['area']} · {d['prioridade']}" for d in todas}
    if (alvo := st.session_state.pop("demanda_alvo", None)) in codigos:
        st.session_state["demanda_sel"] = alvo
        if alvo not in [d["codigo"] for d in filtradas]:
            filtradas.insert(0, banco.obter_demanda_por_codigo(alvo))
    if st.session_state.get("demanda_sel") not in codigos:
        st.session_state["demanda_sel"] = filtradas[0]["codigo"]
    codigo = st.selectbox("Selecione uma demanda para consultar", codigos, format_func=rotulos.get, key="demanda_sel")
    demanda = banco.obter_demanda_por_codigo(codigo)

    c.resumo_demanda(demanda)
    st.write("")
    col1, col2, _ = st.columns([0.22, 0.22, 0.56])
    col1.download_button("Baixar dados JSON", c.json_demanda(demanda), file_name=f"{codigo}.json",
                         mime="application/json", use_container_width=True)
    col2.button("Ver prazos e alertas", on_click=c.ir_para, args=("Prazos e alertas",), use_container_width=True)

    documentos = banco.listar_documentos(demanda["id"])
    notificacoes = banco.listar_notificacoes(demanda["id"])
    abas = st.tabs(["Resumo", "Classificação", f"Documentos ({len(documentos)})", "Triagem",
                    "Histórico", f"Notificações ({len(notificacoes)})"])
    with abas[0]:
        _aba_resumo(demanda)
    with abas[1]:
        _aba_classificacao(demanda)
    with abas[2]:
        _aba_documentos(demanda, documentos)
    with abas[3]:
        _aba_triagem(demanda)
    with abas[4]:
        _aba_historico(demanda)
    with abas[5]:
        _aba_notificacoes(demanda, notificacoes)
    estilo.html('<div class="lf-aviso-rodape">Análise preliminar gerada automaticamente para apoio à decisão. '
                "Não substitui a avaliação de um profissional jurídico.</div>")
