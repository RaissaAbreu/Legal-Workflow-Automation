"""Página: Nova demanda (registro manual pelo painel ou envio pelo fluxo do n8n)."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from datetime import date, timedelta
from html import escape
from typing import Any

import streamlit as st

from legalflow import banco, config, servico
from legalflow.extracao import EXTENSOES_ACEITAS, Anexo
from painel import componentes as c
from painel import estilo

PASTA_EXEMPLOS = config.RAIZ_PROJETO / "exemplos"
TIPOS_UPLOAD = sorted(e.lstrip(".") for e in EXTENSOES_ACEITAS)


def _exemplo_formulario() -> dict[str, Any]:
    return {
        "nd_solicitante": "Carolina Mendes",
        "nd_email": "carolina.mendes@exemplo.com.br",
        "nd_departamento": "Recursos Humanos",
        "nd_assunto": "Notificação do sindicato sobre horas extras",
        "nd_descricao": (
            "Recebemos notificação extrajudicial do sindicato da categoria alegando pagamento incorreto de horas "
            "extras e descumprimento da convenção coletiva para a equipe do turno noturno. Pedem reunião e "
            "apresentação dos cartões de ponto. Precisamos de orientação jurídica antes de responder."
        ),
        "nd_prazo": date.today() + timedelta(days=4),
    }


def _usar_exemplo() -> None:
    st.session_state.update(_exemplo_formulario())
    st.session_state["nd_exemplo_docs"] = True


def _limpar() -> None:
    for chave in ("nd_solicitante", "nd_email", "nd_departamento", "nd_assunto", "nd_descricao"):
        st.session_state[chave] = ""
    st.session_state["nd_prazo"] = None
    st.session_state["nd_exemplo_docs"] = False
    st.session_state["nd_exemplo_eml"] = False
    st.session_state["nd_upload_versao"] = st.session_state.get("nd_upload_versao", 0) + 1


def _documentos_exemplo() -> list[Anexo]:
    arquivo = PASTA_EXEMPLOS / "cartoes_ponto_turno_noturno.txt"
    return [Anexo(arquivo.name, arquivo.read_bytes())] if arquivo.exists() else []


def _enviar_n8n(url: str, corpo: dict[str, Any]) -> dict[str, Any]:
    requisicao = urllib.request.Request(
        url, data=json.dumps(corpo).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(requisicao, timeout=30) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def _lista_arquivos(nomes: list[tuple[str, int]], nota: str = "") -> None:
    if not nomes:
        estilo.html('<div class="lf-muted">Nenhum arquivo selecionado.</div>')
        return
    itens = "".join(
        f'<li><span class="n">{i}</span><span>{escape(nome)}</span>'
        f'<span class="dir lf-muted">{tamanho / 1024:.1f} KB</span></li>'
        for i, (nome, tamanho) in enumerate(nomes, start=1)
    )
    estilo.html(f'<ul class="lf-arquivos">{itens}</ul>' + (f'<div class="lf-muted" style="margin-top:10px">{escape(nota)}</div>' if nota else ""))


def renderizar() -> None:
    estilo.cabecalho(c.EYEBROW_PADRAO, "Nova demanda",
                     "Registro, extração de dados, classificação e encaminhamento de demandas jurídicas.",
                     selo="Modo demonstração")
    estilo.secao("Entrada da demanda / 01", "Registro de demanda",
                 "Preencha o formulário ou envie o e-mail recebido (.eml). Documentos em PDF, TXT, DOCX e EML têm o "
                 "texto lido para a classificação; imagens são apenas armazenadas.")

    if st.session_state.pop("nd_limpar_pendente", False):
        _limpar()

    tipo = st.radio("Tipo de entrada", ["Formulário", "E-mail (.eml)"], horizontal=True, key="nd_tipo")
    versao = st.session_state.get("nd_upload_versao", 0)
    anexos: list[Anexo] = []
    email_bruto: bytes | None = None

    if tipo == "Formulário":
        with st.container(border=True, key="cartao-nd-solicitante"):
            estilo.titulo_cartao("01", "Solicitante")
            col1, col2, col3 = st.columns(3)
            col1.text_input("Nome", key="nd_solicitante")
            col2.text_input("E-mail", key="nd_email")
            col3.text_input("Departamento", key="nd_departamento", placeholder="Ex.: Recursos Humanos")
            b1, b2, _ = st.columns([0.28, 0.16, 0.56])
            b1.button("Usar demanda de exemplo", on_click=_usar_exemplo, use_container_width=True,
                      help="Preenche o formulário com uma demanda fictícia.")
            b2.button("Limpar", on_click=_limpar, use_container_width=True)

        esquerda, direita = st.columns([0.58, 0.42], gap="medium")
        with esquerda:
            with st.container(border=True, key="cartao-nd-demanda"):
                estilo.titulo_cartao("02", "Demanda")
                st.text_input("Assunto", key="nd_assunto")
                st.text_area("Descrição", key="nd_descricao", height=170,
                             placeholder="Descreva a demanda. Prazos citados no texto (ex.: “prazo até 20/11/2026”) são identificados automaticamente.")
                st.date_input("Prazo informado (opcional)", key="nd_prazo", value=None, format="DD/MM/YYYY",
                              help="Se ficar em branco, o sistema procura o prazo no texto. Sem prazo, a demanda é marcada como “prazo a definir”.")
        with direita:
            with st.container(border=True, key="cartao-nd-documentos"):
                estilo.titulo_cartao("03", "Documentos")
                arquivos = st.file_uploader("Anexos", type=TIPOS_UPLOAD, accept_multiple_files=True,
                                            key=f"nd_docs_{versao}", label_visibility="collapsed")
                anexos = [Anexo(a.name, a.getvalue()) for a in arquivos or []]
                if st.session_state.get("nd_exemplo_docs"):
                    anexos += _documentos_exemplo()
                _lista_arquivos([(a.nome, len(a.conteudo)) for a in anexos],
                                "Inclui documento fictício do exemplo." if st.session_state.get("nd_exemplo_docs") else "")
    else:
        with st.container(border=True, key="cartao-nd-email"):
            estilo.titulo_cartao("01", "E-mail recebido")
            arquivo = st.file_uploader("Arquivo .eml", type=["eml"], key=f"nd_eml_{versao}", label_visibility="collapsed")
            b1, b2, _ = st.columns([0.28, 0.16, 0.56])
            b1.button("Usar e-mail de exemplo", use_container_width=True,
                      on_click=lambda: st.session_state.update(nd_exemplo_eml=True),
                      help="Carrega um e-mail fictício com anexo.")
            b2.button("Limpar", on_click=_limpar, use_container_width=True, key="nd_limpar_eml")
            if arquivo is not None:
                email_bruto = arquivo.getvalue()
                nome_eml = arquivo.name
            elif st.session_state.get("nd_exemplo_eml"):
                caminho = PASTA_EXEMPLOS / "email_notificacao_procon.eml"
                email_bruto, nome_eml = caminho.read_bytes(), caminho.name
            if email_bruto:
                from legalflow.extracao import ler_email

                lido = ler_email(email_bruto)
                estilo.html(f"""<ul class="lf-arquivos">
                  <li><span class="n">@</span><div><div>{escape(lido.assunto or '(sem assunto)')}</div>
                  <div class="det">De: {escape(lido.remetente_nome)} &lt;{escape(lido.remetente_email)}&gt; · {escape(nome_eml)}</div></div></li>
                  {''.join(f'<li><span class="n">{i}</span>{escape(a.nome)}<span class="dir lf-muted">{len(a.conteudo) / 1024:.1f} KB</span></li>' for i, a in enumerate(lido.anexos, 1))}
                </ul>""")

    # ------------------------------------------------------------- envio
    url_n8n = config.url_webhook_n8n()
    st.write("")
    usar_n8n = False
    if url_n8n:
        usar_n8n = st.toggle("Enviar pelo fluxo do n8n (registra e notifica o responsável no Teams)", value=True)
    else:
        estilo.html('<div class="lf-muted">Processamento local: o webhook do n8n não está configurado '
                    "(variável LEGALFLOW_N8N_WEBHOOK), então nenhuma notificação será enviada.</div>")
    st.write("")

    if st.button("Registrar demanda", type="primary"):
        ss = st.session_state
        if tipo == "Formulário" and not (ss.get("nd_assunto") or ss.get("nd_descricao") or anexos):
            st.error("Informe ao menos o assunto, a descrição ou um documento.")
            return
        if tipo != "Formulário" and not email_bruto:
            st.error("Envie um arquivo .eml ou use o e-mail de exemplo.")
            return

        prazo = ss.get("nd_prazo") if tipo == "Formulário" else None
        with st.spinner("Extraindo dados, classificando e registrando…"):
            if usar_n8n:
                corpo = {
                    "canal": "Formulário" if tipo == "Formulário" else "E-mail",
                    "solicitante": ss.get("nd_solicitante", "") if tipo == "Formulário" else "",
                    "email_solicitante": ss.get("nd_email", "") if tipo == "Formulário" else "",
                    "departamento": ss.get("nd_departamento", "") if tipo == "Formulário" else "",
                    "assunto": ss.get("nd_assunto", "") if tipo == "Formulário" else "",
                    "descricao": ss.get("nd_descricao", "") if tipo == "Formulário" else "",
                    "prazo": prazo.isoformat() if prazo else None,
                    "documentos": [{"nome": a.nome, "conteudo_base64": base64.b64encode(a.conteudo).decode()} for a in anexos],
                }
                if email_bruto:
                    corpo["email_eml_base64"] = base64.b64encode(email_bruto).decode()
                try:
                    resposta = _enviar_n8n(url_n8n, corpo)
                    demanda = banco.obter_demanda_por_codigo(resposta["demanda"]["codigo"])
                except (urllib.error.URLError, KeyError, ValueError, TimeoutError) as erro:
                    st.error(f"Não foi possível enviar ao n8n ({erro}). Verifique se o fluxo “Entrada de demandas” "
                             "está ativo ou desligue a opção para processar localmente.")
                    return
            else:
                demanda = servico.registrar_demanda(servico.EntradaDemanda(
                    canal="Painel" if tipo == "Formulário" else "E-mail",
                    solicitante=ss.get("nd_solicitante", "") if tipo == "Formulário" else "",
                    email_solicitante=ss.get("nd_email", "") if tipo == "Formulário" else "",
                    departamento=ss.get("nd_departamento", "") if tipo == "Formulário" else "",
                    assunto=ss.get("nd_assunto", "") if tipo == "Formulário" else "",
                    descricao=ss.get("nd_descricao", "") if tipo == "Formulário" else "",
                    prazo=prazo, documentos=anexos, email_bruto=email_bruto,
                ))
        ss["nd_ultima"] = demanda["codigo"]
        ss["nd_limpar_pendente"] = True  # widgets só podem ser limpos antes de serem desenhados
        st.rerun()

    if st.session_state.get("nd_ultima"):
        demanda = banco.obter_demanda_por_codigo(st.session_state["nd_ultima"])
        if demanda:
            st.write("")
            estilo.secao("Resultado / 02", f"Demanda {demanda['codigo']} registrada",
                         "Confira a extração automática. A classificação é preliminar e pode ser corrigida na triagem.")
            c.resumo_demanda(demanda)
            st.button("Abrir na triagem", type="primary", on_click=c.ir_para,
                      args=("Demandas e triagem", demanda["codigo"]))
