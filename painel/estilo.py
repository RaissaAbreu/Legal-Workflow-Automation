"""Identidade visual do painel: CSS e pequenos componentes em HTML."""

from __future__ import annotations

from html import escape

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Source+Sans+3:wght@400;600;700&display=swap');

:root {
  --lf-navy: #13213f;
  --lf-navy-2: #1d2d52;
  --lf-ink: #14213d;
  --lf-texto: #2b2f3a;
  --lf-suave: #5f6472;
  --lf-ouro: #b07d2b;
  --lf-ouro-claro: #d9a441;
  --lf-fundo: #f4f2ec;
  --lf-papel: #faf8f3;
  --lf-cartao: #ffffff;
  --lf-borda: #e6e1d6;
  --lf-borda-forte: #d6d0c2;
}

html, body, .stApp, [class*="css"], .stMarkdown, button, input, textarea, select {
  font-family: 'Source Sans 3', 'Segoe UI', sans-serif;
}
.stApp { background: var(--lf-fundo); color: var(--lf-texto); }
.block-container { padding-top: 3.5rem; max-width: 1180px; }
header[data-testid="stHeader"] { background: transparent; }

/* ---------- barra lateral ---------- */
section[data-testid="stSidebar"] { background: var(--lf-navy); }
section[data-testid="stSidebar"] * { color: #f3f1ea; }
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] svg { fill: #f3f1ea; }
.lf-marca { text-align: center; padding: 8px 0 26px; border-bottom: 1px solid rgba(255,255,255,.14); margin-bottom: 26px; }
.lf-marca .nome { font-family: 'Cormorant Garamond', serif; font-size: 31px; letter-spacing: .16em; white-space: nowrap; color: #fff; font-weight: 500; }
.lf-marca .sub { font-size: 11px; font-weight: 700; letter-spacing: .34em; color: var(--lf-ouro-claro) !important; margin-top: 14px; line-height: 1.7; }
.lf-rotulo-lateral { font-size: 11px; font-weight: 600; letter-spacing: .32em; text-transform: uppercase; color: #f3f1ea; margin: 4px 0 10px; }
.lf-sep { border-top: 1px solid rgba(255,255,255,.14); margin: 22px 0; }
.lf-nota-lateral { font-size: 13px; color: #f3f1ea; display: flex; gap: 6px; align-items: center; margin-top: 10px; }
.lf-nota-lateral .ponto { width: 9px; height: 9px; border-radius: 50%; background: #fff; display: inline-block; }
.lf-nota-lateral .ponto.ok { background: #7cc79a; } .lf-nota-lateral .ponto.off { background: #8a90a3; }
.lf-rodape-lateral .titulo { font-size: 16px; margin-bottom: 4px; line-height: 1.5; }
.lf-rodape-lateral .meta { font-size: 13px; color: #a9afc0 !important; line-height: 1.6; }
section[data-testid="stSidebar"] [role="radiogroup"] label p { font-size: 17px; }
section[data-testid="stSidebar"] [role="radiogroup"] { gap: 4px; }
section[data-testid="stSidebar"] [data-baseweb="select"] > div { background: var(--lf-navy-2); border-color: rgba(255,255,255,.35); }
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { font-size: 14px; }

/* ---------- tipografia ---------- */
.lf-eyebrow { font-size: 11px; font-weight: 700; letter-spacing: .32em; text-transform: uppercase; color: var(--lf-ouro); margin-bottom: 8px; }
.lf-titulo { font-family: 'Cormorant Garamond', serif; font-weight: 500; font-size: 52px; line-height: 1.1; color: var(--lf-ink); margin: 6px 0 0; }
.lf-subtitulo { color: var(--lf-suave); font-size: 15.5px; margin-top: 8px; }
.lf-cabecalho { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding-bottom: 28px; border-bottom: 1px solid var(--lf-borda-forte); margin-bottom: 30px; }
.lf-selo { background: #f6e9c9; border: 1px solid #ecd59c; color: #6b4a10; border-radius: 999px; padding: 14px 28px; font-weight: 700; white-space: nowrap; }
.lf-selo::before { content: "●"; margin-right: 6px; }
.lf-secao-titulo { font-family: 'Cormorant Garamond', serif; font-weight: 500; font-size: 38px; color: var(--lf-ink); margin: 6px 0 4px; }
.lf-secao-texto { color: var(--lf-texto); font-size: 15px; margin-bottom: 18px; }
.lf-cartao-titulo { font-weight: 700; font-size: 17px; color: var(--lf-ink); margin-bottom: 10px; }
.lf-cartao-titulo .num { margin-right: 8px; }
.lf-rotulo { font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #2a3f6e; margin: 14px 0 8px; }
.lf-muted { color: var(--lf-suave); font-size: 14px; }

/* ---------- cartões ---------- */
div[class*="st-key-cartao"] {
  background: var(--lf-cartao); border: 1px solid var(--lf-borda) !important; border-radius: 18px;
  padding: 28px 32px; box-shadow: 0 2px 10px rgba(20, 33, 61, .04);
}

/* ---------- métricas ---------- */
.lf-metricas { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 16px; padding: 4px 0 26px; border-bottom: 1px solid var(--lf-borda-forte); margin-bottom: 26px; }
.lf-metrica .rotulo { font-weight: 700; color: var(--lf-ink); font-size: 16px; }
.lf-metrica .valor { font-weight: 700; color: var(--lf-ink); font-size: 40px; line-height: 1.2; }
.lf-metrica .valor.alerta { color: #a23b22; }
.lf-metrica .nota { font-size: 13px; color: var(--lf-suave); }

/* ---------- selos ---------- */
.lf-badge { display: inline-block; border-radius: 999px; padding: 4px 14px; font-size: 12.5px; font-weight: 700; border: 1px solid; margin: 2px 6px 2px 0; white-space: nowrap; }
.lf-badge.vermelho { background: #f9e0dc; color: #9b2c1f; border-color: #f0c4bd; }
.lf-badge.ambar    { background: #f8ecd0; color: #7a5212; border-color: #ecd59c; }
.lf-badge.azul     { background: #e5ebf6; color: #2a3f6e; border-color: #cbd6ec; }
.lf-badge.verde    { background: #dff0e4; color: #2a6a41; border-color: #bfdfc9; }
.lf-badge.neutro   { background: #f0eee8; color: #4b4f5c; border-color: #dedad0; }

/* ---------- destaque de prioridade (caixa grande) ---------- */
.lf-risco { border-radius: 16px; padding: 30px 32px; height: 100%; min-height: 220px; }
.lf-risco .rotulo { font-size: 11.5px; font-weight: 700; letter-spacing: .3em; text-transform: uppercase; }
.lf-risco .valor { font-family: 'Cormorant Garamond', serif; font-size: 76px; line-height: 1.05; margin: 6px 0 8px; }
.lf-risco .nota { font-weight: 700; font-size: 16px; }
.lf-risco.Crítica { background: #f6e1da; color: #a23b22; }
.lf-risco.Alta    { background: #f7ecd5; color: #8a5a14; }
.lf-risco.Média   { background: #e7ecf6; color: #2a3f6e; }
.lf-risco.Baixa   { background: #e2f0e6; color: #2a6a41; }
.lf-risco.Encerrada { background: #efede7; color: #4b4f5c; }

.lf-lista { margin: 0; padding-left: 20px; color: var(--lf-texto); }
.lf-lista li { margin: 6px 0; font-size: 15.5px; }

/* ---------- bloco de recomendação ---------- */
.lf-recomendacao { background: var(--lf-papel); border-left: 4px solid var(--lf-ouro); border-radius: 0 12px 12px 0; padding: 18px 24px; margin: 14px 0 18px; }
.lf-recomendacao .texto { font-family: 'Cormorant Garamond', serif; font-size: 25px; color: var(--lf-ink); line-height: 1.3; }

/* ---------- itens de demanda ---------- */
.lf-item-cab { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.lf-item-titulo { font-weight: 700; font-size: 17px; color: var(--lf-ink); }
.lf-item-titulo .codigo { margin-right: 8px; }
.lf-item-meta { color: var(--lf-suave); font-size: 15px; margin-top: 4px; }

/* ---------- lista numerada de arquivos ---------- */
.lf-arquivos { list-style: none; padding: 0; margin: 0; }
.lf-arquivos li { display: flex; align-items: center; gap: 14px; padding: 13px 18px; border-bottom: 1px solid #efebe2; font-size: 15.5px; }
.lf-arquivos li:last-child { border-bottom: none; }
.lf-arquivos .n { width: 24px; height: 24px; border-radius: 50%; background: #e7ecf6; color: #2a3f6e; font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; flex: none; }
.lf-arquivos .n.x { background: #f9e0dc; color: #9b2c1f; }
.lf-arquivos .det { color: var(--lf-suave); font-size: 13.5px; margin-top: 2px; }
.lf-arquivos .dir { margin-left: auto; }

/* ---------- barras ---------- */
.lf-barras { display: grid; gap: 12px; }
.lf-barra { display: grid; grid-template-columns: 130px 1fr 34px; align-items: center; gap: 12px; font-size: 15px; }
.lf-barra .trilho { background: #f0ede5; border-radius: 4px; height: 12px; overflow: hidden; }
.lf-barra .preenchido { background: var(--lf-navy-2); height: 100%; border-radius: 0 4px 4px 0; min-width: 2px; }
.lf-barra .preenchido.vazio { background: transparent; }
.lf-barra .num { text-align: right; font-weight: 700; color: var(--lf-ink); font-variant-numeric: tabular-nums; }

/* ---------- linha do tempo ---------- */
.lf-tempo { list-style: none; margin: 0; padding: 0; }
.lf-tempo li { position: relative; padding: 0 0 18px 26px; border-left: 2px solid var(--lf-borda); margin-left: 6px; }
.lf-tempo li::before { content: ""; position: absolute; left: -7px; top: 3px; width: 12px; height: 12px; border-radius: 50%; background: var(--lf-ouro); border: 2px solid #fff; }
.lf-tempo .evento { font-weight: 700; color: var(--lf-ink); }
.lf-tempo .quando { color: var(--lf-suave); font-size: 13px; }

/* ---------- passos (como funciona) ---------- */
.lf-passo { display: flex; gap: 18px; padding: 16px 0; border-bottom: 1px solid #efebe2; }
.lf-passo:last-child { border-bottom: none; }
.lf-passo .n { font-family: 'Cormorant Garamond', serif; font-size: 34px; color: var(--lf-ouro); line-height: 1; min-width: 44px; }
.lf-passo .t { font-weight: 700; color: var(--lf-ink); font-size: 16.5px; }
.lf-passo .d { color: var(--lf-suave); font-size: 14.5px; margin-top: 2px; }

/* ---------- widgets ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius: 8px; padding: .65rem 1.6rem; border: 1px solid var(--lf-navy); background: #fff; color: var(--lf-navy); font-weight: 500;
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--lf-ouro); color: var(--lf-navy); }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {
  background: var(--lf-navy); color: #fff; border-color: var(--lf-navy);
}
.stButton > button[kind="primary"]:hover { background: var(--lf-navy-2); color: #fff; }
.stTextInput input, .stTextArea textarea, .stDateInput input, [data-baseweb="select"] > div, [data-testid="stFileUploaderDropzone"] {
  background: var(--lf-papel) !important;
}
[data-testid="stFileUploaderDropzone"] { border: 1px dashed #e2c9a0; }
.stTabs [data-baseweb="tab-list"] { gap: 18px; border-bottom: 1px solid var(--lf-borda-forte); }
.stTabs [data-baseweb="tab"] { padding: 8px 0; }
.stTabs [aria-selected="true"] p { color: var(--lf-ink); }
.stTabs [data-baseweb="tab-highlight"] { background: var(--lf-ouro); }
.lf-aviso-rodape { color: var(--lf-suave); font-size: 14.5px; margin-top: 14px; }

@media (max-width: 760px) {
  .lf-titulo { font-size: 38px; }
  .lf-cabecalho { flex-direction: column; }
  div[class*="st-key-cartao"] { padding: 20px; }
  .lf-barra { grid-template-columns: 100px 1fr 30px; }
}
</style>
"""

TOM_PRIORIDADE = {"Crítica": "vermelho", "Alta": "ambar", "Média": "azul", "Baixa": "verde"}
TOM_STATUS = {
    "Nova": "azul", "Em triagem": "ambar", "Encaminhada": "azul", "Em andamento": "azul",
    "Aguardando terceiros": "neutro", "Concluída": "verde", "Cancelada": "neutro",
}
TOM_SITUACAO = {
    "vencida": ("Prazo vencido", "vermelho"), "vence_hoje": ("Vence hoje", "vermelho"),
    "vence_em_breve": ("Vence em breve", "ambar"), "no_prazo": ("No prazo", "verde"),
    "prazo_a_definir": ("Prazo a definir", "ambar"), "encerrada": ("Encerrada", "neutro"),
}


def aplicar() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def html(conteudo: str) -> None:
    st.markdown(conteudo, unsafe_allow_html=True)


def badge(texto: str, tom: str = "neutro") -> str:
    return f'<span class="lf-badge {tom}">{escape(str(texto))}</span>'


def cabecalho(eyebrow: str, titulo: str, subtitulo: str, selo: str | None = None) -> None:
    selo_html = f'<div class="lf-selo">{escape(selo)}</div>' if selo else ""
    html(f"""<div class="lf-cabecalho"><div>
      <div class="lf-eyebrow">{escape(eyebrow)}</div>
      <div class="lf-titulo">{escape(titulo)}</div>
      <div class="lf-subtitulo">{escape(subtitulo)}</div></div>{selo_html}</div>""")


def secao(eyebrow: str, titulo: str, texto: str = "") -> None:
    html(f"""<div class="lf-eyebrow">{escape(eyebrow)}</div>
    <div class="lf-secao-titulo">{escape(titulo)}</div>
    {f'<div class="lf-secao-texto">{escape(texto)}</div>' if texto else ''}""")


def titulo_cartao(numero: str | None, texto: str) -> None:
    num = f'<span class="num">{escape(numero)}</span>' if numero else ""
    html(f'<div class="lf-cartao-titulo">{num}{escape(texto)}</div>')


def metricas(itens: list[tuple[str, int | str, bool]]) -> None:
    """itens: (rótulo, valor, destacar_em_vermelho)."""
    blocos = "".join(
        f'<div class="lf-metrica"><div class="rotulo">{escape(r)}</div>'
        f'<div class="valor{" alerta" if alerta and v else ""}">{escape(str(v))}</div></div>'
        for r, v, alerta in itens
    )
    html(f'<div class="lf-metricas">{blocos}</div>')


def barras(contagens: dict[str, int]) -> None:
    """Barras horizontais de uma só cor (magnitude). O número fica sempre visível ao lado."""
    maximo = max(contagens.values(), default=0) or 1
    linhas = "".join(
        f'<div class="lf-barra" title="{escape(k)}: {v}"><span>{escape(k)}</span>'
        f'<div class="trilho"><div class="preenchido{" vazio" if not v else ""}" style="width:{v / maximo * 100:.0f}%"></div></div>'
        f'<span class="num">{v}</span></div>'
        for k, v in contagens.items()
    )
    html(f'<div class="lf-barras">{linhas}</div>')


def recomendacao(eyebrow: str, texto: str) -> None:
    html(f'<div class="lf-recomendacao"><div class="lf-eyebrow">{escape(eyebrow)}</div>'
         f'<div class="texto">{escape(texto)}</div></div>')
