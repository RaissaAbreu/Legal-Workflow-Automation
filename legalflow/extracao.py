"""Extração de informações de e-mails, documentos e textos livres.

Tudo aqui é determinístico (regex + bibliotecas padrão): nenhum dado sai da máquina.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
from html import unescape
from pathlib import Path

from .texto import normalizar, normalizar_1a1

EXTENSOES_TEXTO = {".txt", ".md"}
EXTENSOES_IMAGEM = {".png", ".jpg", ".jpeg", ".webp"}
EXTENSOES_ACEITAS = EXTENSOES_TEXTO | EXTENSOES_IMAGEM | {".pdf", ".eml", ".docx"}

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

# Palavras que, perto de uma data, indicam que ela é um prazo.
GATILHOS_PRAZO = (
    "prazo", "ate", "vence", "vencimento", "data limite", "audiencia", "entregar",
    "responder", "manifestar", "apresentar", "protocolar", "limite",
)


@dataclass
class Anexo:
    nome: str
    conteudo: bytes


@dataclass
class EmailLido:
    remetente_nome: str = ""
    remetente_email: str = ""
    assunto: str = ""
    corpo: str = ""
    data: datetime | None = None
    anexos: list[Anexo] = field(default_factory=list)


@dataclass
class PrazoExtraido:
    data: date
    trecho: str


# --------------------------------------------------------------------------- e-mail


def _html_para_texto(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", html)
    return unescape(re.sub(r"<[^>]+>", " ", html))


def ler_email(bruto: bytes | str) -> EmailLido:
    """Lê um e-mail no formato .eml (RFC 822) e devolve remetente, assunto, corpo e anexos."""
    if isinstance(bruto, str):
        bruto = bruto.encode("utf-8")
    msg = BytesParser(policy=policy.default).parsebytes(bruto)

    nome, endereco = parseaddr(str(msg.get("From", "")))
    lido = EmailLido(remetente_nome=nome.strip(), remetente_email=endereco.strip(),
                     assunto=str(msg.get("Subject", "")).strip())
    try:
        lido.data = parsedate_to_datetime(str(msg["Date"])) if msg["Date"] else None
    except (TypeError, ValueError):
        lido.data = None

    corpo = msg.get_body(preferencelist=("plain", "html"))
    if corpo is not None:
        conteudo = corpo.get_content()
        lido.corpo = _html_para_texto(conteudo) if corpo.get_content_type() == "text/html" else conteudo
    lido.corpo = lido.corpo.strip()

    for parte in msg.iter_attachments():
        nome_arquivo = parte.get_filename()
        if not nome_arquivo:
            continue
        dados = parte.get_payload(decode=True) or b""
        lido.anexos.append(Anexo(nome=nome_arquivo, conteudo=dados))
    return lido


# --------------------------------------------------------------------------- documentos


def extrair_texto_documento(nome: str, conteudo: bytes) -> str:
    """Extrai texto de TXT, PDF, EML e DOCX. Imagens não têm texto extraído (sem OCR)."""
    ext = Path(nome).suffix.lower()
    try:
        if ext in EXTENSOES_TEXTO:
            for codificacao in ("utf-8", "latin-1"):
                try:
                    return conteudo.decode(codificacao)
                except UnicodeDecodeError:
                    continue
        if ext == ".pdf":
            from pypdf import PdfReader

            leitor = PdfReader(io.BytesIO(conteudo))
            return "\n".join((pagina.extract_text() or "") for pagina in leitor.pages)
        if ext == ".eml":
            lido = ler_email(conteudo)
            return f"{lido.assunto}\n{lido.corpo}"
        if ext == ".docx":
            import zipfile

            with zipfile.ZipFile(io.BytesIO(conteudo)) as zf:
                xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
            return unescape(re.sub(r"<[^>]+>", " ", xml.replace("</w:p>", "\n")))
    except Exception:  # documento corrompido não pode derrubar o registro da demanda
        return ""
    return ""


# --------------------------------------------------------------------------- prazo


def somar_dias_uteis(inicio: date, dias: int) -> date:
    """Soma dias úteis (segunda a sexta). Não considera feriados."""
    atual = inicio
    restantes = dias
    while restantes > 0:
        atual += timedelta(days=1)
        if atual.weekday() < 5:
            restantes -= 1
    return atual


def _data_valida(dia: int, mes: int, ano: int) -> date | None:
    if ano < 100:
        ano += 2000
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def _trecho(texto: str, inicio: int, fim: int) -> str:
    """Recorta o trecho original que contém o prazo, começando no início da frase."""
    janela = max(0, inicio - 70)
    separador = max(texto.rfind(sep, janela, inicio) for sep in (". ", ";", "\n"))
    if separador != -1:
        ini = separador + 1
    elif janela > 0:  # sem início de frase por perto: começa na próxima palavra inteira
        espaco = texto.find(" ", janela, inicio)
        ini = espaco + 1 if espaco != -1 else janela
    else:
        ini = 0
    return re.sub(r"\s+", " ", texto[ini:fim]).strip(" ,—-")


_RE_GATILHO = re.compile(r"(?<![a-z])(?:" + "|".join(re.escape(g) for g in GATILHOS_PRAZO) + r")(?![a-z])")


def _tem_gatilho(texto_norm: str, inicio: int) -> bool:
    """Há uma palavra de prazo (inteira) nos 60 caracteres antes da data?"""
    return bool(_RE_GATILHO.search(texto_norm[max(0, inicio - 60):inicio]))


def extrair_prazo(texto: str, referencia: date) -> PrazoExtraido | None:
    """Procura um prazo no texto.

    Ordem de busca:
    1. Datas explícitas (dd/mm/aaaa ou "10 de dezembro de 2026") precedidas de palavras
       como "prazo", "até", "vencimento", "audiência". Se houver mais de uma, vale a mais próxima.
    2. Prazos relativos: "prazo de 5 dias úteis", "em 10 dias", "em 48 horas".
    """
    norm = normalizar_1a1(texto)
    candidatos: list[PrazoExtraido] = []

    for m in re.finditer(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b", norm):
        if _tem_gatilho(norm, m.start()):
            d = _data_valida(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if d:
                candidatos.append(PrazoExtraido(d, _trecho(texto, m.start(), m.end())))

    padrao_extenso = r"\b(\d{1,2}) de (" + "|".join(MESES) + r")(?: de (\d{4}))?"
    for m in re.finditer(padrao_extenso, norm):
        if _tem_gatilho(norm, m.start()):
            ano = int(m.group(3)) if m.group(3) else referencia.year
            d = _data_valida(int(m.group(1)), MESES[m.group(2)], ano)
            if d and not m.group(3) and d < referencia:
                d = _data_valida(d.day, d.month, ano + 1)
            if d:
                candidatos.append(PrazoExtraido(d, _trecho(texto, m.start(), m.end())))

    if candidatos:
        return min(candidatos, key=lambda c: c.data)

    m = re.search(r"(?:\bprazo\b[^.\n\d]{0,40}?|\b(?:em|dentro de)\s+)(\d{1,3})\s*(?:\(\w+\)\s*)?dias?\s*(uteis|corridos)?", norm)
    if m:
        dias = int(m.group(1))
        uteis = m.group(2) == "uteis"
        d = somar_dias_uteis(referencia, dias) if uteis else referencia + timedelta(days=dias)
        return PrazoExtraido(d, _trecho(texto, m.start(), m.end()))

    m = re.search(r"(?:\bprazo\b[^.\n\d]{0,40}?|\b(?:em|dentro de)\s+)(\d{1,3})\s*horas", norm)
    if m:
        horas = int(m.group(1))
        return PrazoExtraido(referencia + timedelta(days=max(1, -(-horas // 24))), _trecho(texto, m.start(), m.end()))

    return None


# --------------------------------------------------------------------------- campos


def _campo_rotulado(texto: str, rotulos: tuple[str, ...]) -> str:
    """Procura linhas do tipo 'Rótulo: valor' (comuns em formulários e e-mails)."""
    for rotulo in rotulos:
        m = re.search(rf"(?im)^\s*{rotulo}\s*[:\-]\s*(.+?)\s*$", texto)
        if m:
            return m.group(1).strip()
    return ""


def extrair_solicitante(texto: str) -> str:
    return _campo_rotulado(texto, ("solicitante", "nome do solicitante", "requerente", "nome"))


def extrair_departamento(texto: str) -> str:
    return _campo_rotulado(texto, ("departamento", "area solicitante", "área solicitante", "setor", "área", "area"))


def extrair_email(texto: str) -> str:
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", texto or "")
    return m.group(0) if m else ""
