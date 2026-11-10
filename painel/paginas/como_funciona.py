"""Página: Como funciona (fluxo, regras de classificação e de prioridade)."""

from __future__ import annotations

from html import escape

import streamlit as st

from legalflow import config
from legalflow.classificacao import MOTOR, TERMOS_POR_AREA
from legalflow.constantes import STATUS
from legalflow.prioridade import TERMOS_ALTOS, TERMOS_CRITICOS, TERMOS_MEDIOS
from painel import componentes as c
from painel import estilo

PASSOS = [
    ("Recebimento", "A demanda chega por formulário ou e-mail ao webhook do n8n (fluxo “Entrada de demandas”), "
                    "ou é registrada diretamente aqui no painel."),
    ("Extração", "Python lê o e-mail (.eml), os anexos em PDF, TXT e DOCX e identifica solicitante, departamento, "
                 "assunto, prazo e documentos."),
    ("Classificação", "O motor de regras pontua termos característicos de cada área: trabalhista, cível, consumidor, "
                      "contratual ou regulatória."),
    ("Prioridade", "O prazo e palavras de urgência (liminar, audiência, autuação…) definem a prioridade sugerida."),
    ("Registro", "A demanda, os documentos e o histórico são gravados no SQLite."),
    ("Encaminhamento", "O responsável ativo da área com menos demandas em aberto recebe a demanda e é avisado no "
                       "Microsoft Teams pelo n8n. Sem responsável ou com baixa confiança, a demanda vai para triagem."),
    ("Monitoramento", "De hora em hora o n8n (fluxo “Monitor de prazos”) consulta os alertas pendentes e avisa sobre "
                      "prazos vencidos, que vencem hoje, próximos do vencimento ou sem prazo definido."),
]


def renderizar() -> None:
    estilo.cabecalho(c.EYEBROW_PADRAO, "Como funciona",
                     "O caminho de uma demanda jurídica, do recebimento ao acompanhamento do prazo.")

    estilo.secao("Fluxo / 06", "Etapas da automação")
    with st.container(border=True, key="cartao-passos"):
        estilo.html("".join(
            f'<div class="lf-passo"><div class="n">{i:02d}</div><div><div class="t">{escape(t)}</div>'
            f'<div class="d">{escape(d)}</div></div></div>'
            for i, (t, d) in enumerate(PASSOS, start=1)
        ))

    st.write("")
    estilo.secao("Regras / 07", "Prioridade sugerida",
                 "A prioridade final é a mais alta entre a indicada pelo prazo e a indicada pelos termos de urgência.")
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        with st.container(border=True, key="cartao-regra-prazo"):
            estilo.titulo_cartao(None, "Pelo prazo (dias corridos)")
            estilo.html(f"""<ul class="lf-lista">
              <li>{estilo.badge('Crítica', 'vermelho')} vencido ou até 2 dias</li>
              <li>{estilo.badge('Alta', 'ambar')} de 3 a 5 dias</li>
              <li>{estilo.badge('Média', 'azul')} de 6 a 15 dias, ou sem prazo informado</li>
              <li>{estilo.badge('Baixa', 'verde')} mais de 15 dias</li></ul>
              <div class="lf-muted" style="margin-top:10px">Sem prazo, a demanda é marcada como “prazo a definir” e
              gera alerta após {config.horas_alerta_prazo_a_definir()} horas.</div>""")
    with col2:
        with st.container(border=True, key="cartao-regra-termos"):
            estilo.titulo_cartao(None, "Pelos termos de urgência")
            for nivel, tom, termos in (("Crítica", "vermelho", TERMOS_CRITICOS), ("Alta", "ambar", TERMOS_ALTOS),
                                       ("Média", "azul", TERMOS_MEDIOS)):
                estilo.html(f'<div class="lf-rotulo">{nivel}</div><div>'
                            + "".join(estilo.badge(t, tom) for t in termos) + "</div>")

    st.write("")
    estilo.secao("Regras / 08", "Classificação por área",
                 f"{MOTOR}: termos com peso 3 são muito característicos da área; peso 1 é um indício fraco. "
                 "Nenhum dado é enviado a serviços externos.")
    with st.container(border=True, key="cartao-regra-areas"):
        for area, termos in TERMOS_POR_AREA.items():
            with st.expander(f"{area} · {len(termos)} termos"):
                ordenados = sorted(termos.items(), key=lambda t: (-t[1], t[0]))
                estilo.html("".join(estilo.badge(f"{t} · {p}", {3: "azul", 2: "neutro", 1: "neutro"}[p]) for t, p in ordenados))

    st.write("")
    estilo.secao("Regras / 09", "Status de uma demanda")
    with st.container(border=True, key="cartao-status"):
        estilo.html(" → ".join(estilo.badge(s, estilo.TOM_STATUS[s]) for s in STATUS[:-1])
                    + f' <span class="lf-muted">· a qualquer momento:</span> {estilo.badge(STATUS[-1], "neutro")}')
