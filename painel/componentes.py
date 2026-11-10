"""Componentes reutilizados entre as páginas do painel."""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from typing import Any

import streamlit as st

from legalflow import banco, servico
from legalflow.constantes import AREAS, STATUS_FINAIS
from painel import estilo

PAGINAS = ["Visão geral", "Nova demanda", "Demandas e triagem", "Prazos e alertas", "Responsáveis", "Como funciona"]
EYEBROW_PADRAO = "Operações jurídicas / Legal Flow"


def ir_para(pagina: str, codigo: str | None = None) -> None:
    """Callback de navegação (usar em on_click)."""
    st.session_state["pagina"] = pagina
    if codigo:
        # chave fora de widget: o Streamlit descarta o estado de widgets de páginas não exibidas
        st.session_state["demanda_alvo"] = codigo


def data_hora(valor: str | None) -> str:
    if not valor:
        return "—"
    return datetime.fromisoformat(valor).strftime("%d/%m/%Y %H:%M")


def texto_prazo(demanda: dict[str, Any]) -> str:
    dias = servico.dias_ate_prazo(demanda)
    if dias is None:
        return "Prazo a definir"
    data = servico.formatar_data(demanda["prazo"])
    if demanda["status"] in STATUS_FINAIS:
        return f"Prazo {data}"
    if dias < 0:
        return f"Vencido há {-dias} dia(s) · {data}"
    if dias == 0:
        return f"Vence hoje · {data}"
    return f"Prazo em {dias} dia(s) · {data}"


def badges_demanda(demanda: dict[str, Any], incluir_situacao: bool = True) -> str:
    partes = []
    if incluir_situacao:
        rotulo, tom = estilo.TOM_SITUACAO[servico.situacao_prazo(demanda)]
        if tom != "verde":
            partes.append(estilo.badge(rotulo, tom))
    partes.append(estilo.badge(f"Prioridade {demanda['prioridade'].lower()}", estilo.TOM_PRIORIDADE[demanda["prioridade"]]))
    partes.append(estilo.badge(demanda["area"], "neutro"))
    partes.append(estilo.badge(demanda["status"], estilo.TOM_STATUS.get(demanda["status"], "neutro")))
    return "".join(partes)


def item_demanda(demanda: dict[str, Any], chave: str) -> None:
    """Cartão compacto de uma demanda, no estilo da 'Central de revisão'."""
    with st.container(border=True, key=f"cartao-item-{chave}-{demanda['id']}"):
        estilo.html(f"""<div class="lf-item-cab">
          <div class="lf-item-titulo"><span class="codigo">{escape(demanda['codigo'])}</span>{escape(demanda['assunto'])}</div>
          <div>{badges_demanda(demanda)}</div></div>
          <div class="lf-item-meta">{escape(demanda['solicitante'])}{(' · ' + escape(demanda['departamento'])) if demanda['departamento'] else ''}
          · Recebida em {data_hora(demanda['recebida_em'])} · {demanda['qtd_documentos']} documento(s)
          · Responsável: {escape(demanda.get('responsavel_nome') or 'sem responsável')}</div>""")
        estilo.recomendacao("Prazo", texto_prazo(demanda))
        st.button("Abrir demanda", key=f"abrir-{chave}-{demanda['id']}",
                  on_click=ir_para, args=("Demandas e triagem", demanda["codigo"]))


def resumo_demanda(demanda: dict[str, Any]) -> None:
    """Bloco principal do detalhe: prioridade em destaque + classificação + dados principais."""
    with st.container(border=True, key=f"cartao-resumo-{demanda['id']}"):
        esquerda, direita = st.columns([0.42, 0.58], gap="large")
        encerrada = demanda["status"] in STATUS_FINAIS
        classe = "Encerrada" if encerrada else demanda["prioridade"]
        with esquerda:
            estilo.html(f"""<div class="lf-risco {classe}">
              <div class="rotulo">Prioridade{' sugerida' if demanda['prioridade'] == demanda['prioridade_sugerida'] else ' definida'}</div>
              <div class="valor">{escape(demanda['prioridade'])}</div>
              <div class="nota">{escape(texto_prazo(demanda))}</div></div>""")
        with direita:
            confianca = f"Confiança {demanda['confianca']:.0%}" if demanda["area"] == demanda["area_sugerida"] else "Área corrigida na triagem"
            termos = demanda["termos"].get(demanda["area"], []) if demanda["termos"] else []
            responsavel = demanda.get("responsavel_nome") or "Sem responsável — aguardando triagem"
            prazo_origem = f" ({demanda['prazo_origem']})" if demanda["prazo_origem"] else ""
            estilo.html(f"""
              <div class="lf-rotulo" style="margin-top:0">Classificação preliminar</div>
              <div>{estilo.badge(demanda['area'], 'azul')}{estilo.badge(confianca, 'neutro')}{estilo.badge(demanda['status'], estilo.TOM_STATUS.get(demanda['status'], 'neutro'))}</div>
              <div class="lf-rotulo">Dados principais</div>
              <ul class="lf-lista">
                <li>{escape(demanda['codigo'])} · {escape(demanda['assunto'])}</li>
                <li>Solicitante: {escape(demanda['solicitante'])}{(' · ' + escape(demanda['departamento'])) if demanda['departamento'] else ''}{(' · ' + escape(demanda['email_solicitante'])) if demanda['email_solicitante'] else ''}</li>
                <li>Canal: {escape(demanda['canal'])} · recebida em {data_hora(demanda['recebida_em'])}</li>
                <li>Prazo: {escape(servico.formatar_data(demanda['prazo']) if demanda['prazo'] else 'a definir')}{escape(prazo_origem)}</li>
                <li>Responsável: {escape(responsavel)}</li>
              </ul>
              <div class="lf-rotulo">Termos identificados</div>
              <div>{''.join(estilo.badge(t, 'verde') for t in termos) or '<span class="lf-muted">Nenhum termo característico encontrado.</span>'}</div>
            """)


def json_demanda(demanda: dict[str, Any]) -> str:
    dados = {k: v for k, v in demanda.items() if k != "responsavel_teams_webhook"}
    dados["documentos"] = [{k: d[k] for k in ("nome", "tamanho", "caracteres_texto")}
                           for d in banco.listar_documentos(demanda["id"])]
    dados["historico"] = banco.listar_historico(demanda["id"])
    return json.dumps(dados, ensure_ascii=False, indent=2)


def opcoes_responsavel(area: str | None = None) -> dict[int | None, str]:
    opcoes: dict[int | None, str] = {None: "Sem responsável"}
    responsaveis = banco.listar_responsaveis(apenas_ativos=True)
    responsaveis.sort(key=lambda r: (r["area"] != area, r["area"], r["nome"]))
    for r in responsaveis:
        opcoes[r["id"]] = f"{r['nome']} · {r['area']} ({r['demandas_abertas']} em aberto)"
    return opcoes


def contagem_por(demandas: list[dict[str, Any]], campo: str, ordem: list[str]) -> dict[str, int]:
    contagem = {chave: 0 for chave in ordem}
    for d in demandas:
        contagem[d[campo]] = contagem.get(d[campo], 0) + 1
    return contagem
