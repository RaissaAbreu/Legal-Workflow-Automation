"""Utilitários de texto."""

import re
import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos e com espaços simples — base para comparar termos."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def contem_termo(texto_normalizado: str, termo: str) -> int:
    """Quantas vezes o termo (normalizado) aparece como palavra/expressão inteira."""
    padrao = r"(?<![a-z0-9])" + re.escape(normalizar(termo)) + r"(?![a-z0-9])"
    return len(re.findall(padrao, texto_normalizado))


def resumir(texto: str, limite: int = 180) -> str:
    texto = re.sub(r"\s+", " ", texto or "").strip()
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def normalizar_1a1(texto: str) -> str:
    """Como normalizar(), mas mantém o mesmo tamanho do texto original (1 caractere -> 1 caractere).

    Permite procurar no texto normalizado e recortar o trecho correspondente do original.
    """
    saida = []
    for c in texto or "":
        base = "".join(x for x in unicodedata.normalize("NFKD", c) if not unicodedata.combining(x))
        saida.append((base[:1] or c).lower())
    return "".join(saida)
