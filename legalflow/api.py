"""API HTTP consumida pelo n8n.

Rotas principais:
    POST /demandas            registra uma demanda (formulário ou e-mail) e devolve a notificação a enviar
    GET  /alertas/pendentes   alertas de prazo que o n8n deve enviar agora
    POST /notificacoes        o n8n informa o resultado do envio (para não repetir alertas)
"""

from __future__ import annotations

import base64
import binascii
from contextlib import asynccontextmanager
from datetime import date
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import VERSAO, banco, servico
from .constantes import CANAIS, SITUACOES_NOTIFICACAO, TIPOS_NOTIFICACAO
from .extracao import Anexo



@asynccontextmanager
async def _ciclo_de_vida(_: FastAPI):
    banco.inicializar()
    yield


app = FastAPI(title="LEGAL FLOW API", version=VERSAO, lifespan=_ciclo_de_vida,
              description="Registro, classificação e monitoramento de demandas jurídicas.")


class DocumentoEntrada(BaseModel):
    nome: str
    conteudo_base64: str = Field(description="Conteúdo do arquivo em Base64")


class DemandaEntrada(BaseModel):
    canal: str = Field("Formulário", description=f"Um de: {', '.join(CANAIS)}")
    solicitante: str = ""
    email_solicitante: str = ""
    departamento: str = ""
    assunto: str = ""
    descricao: str = ""
    prazo: date | None = Field(None, description="Prazo informado (AAAA-MM-DD). Opcional.")
    documentos: list[DocumentoEntrada] = []
    email_eml_base64: str | None = Field(None, description="E-mail completo (.eml) em Base64")
    email_eml: str | None = Field(None, description="E-mail completo (.eml) em texto puro")


class NotificacaoEntrada(BaseModel):
    demanda_id: int
    tipo: Literal[tuple(TIPOS_NOTIFICACAO)]  # type: ignore[valid-type]
    situacao: Literal[tuple(SITUACOES_NOTIFICACAO)]  # type: ignore[valid-type]
    destino: str = ""


def _b64(valor: str, campo: str) -> bytes:
    try:
        return base64.b64decode(valor, validate=True)
    except (binascii.Error, ValueError) as erro:
        raise HTTPException(422, f"{campo}: Base64 inválido") from erro


@app.get("/saude")
def saude() -> dict[str, Any]:
    return {"status": "ok", "versao": VERSAO, "demandas": banco.contar_demandas()}


@app.post("/demandas", status_code=201)
def criar_demanda(entrada: DemandaEntrada) -> dict[str, Any]:
    email_bruto = None
    if entrada.email_eml_base64:
        email_bruto = _b64(entrada.email_eml_base64, "email_eml_base64")
    elif entrada.email_eml:
        email_bruto = entrada.email_eml.encode("utf-8")

    if not (entrada.assunto or entrada.descricao or email_bruto or entrada.documentos):
        raise HTTPException(422, "Informe assunto, descrição, e-mail ou documentos.")

    canal = entrada.canal if entrada.canal in CANAIS else "Formulário"
    if email_bruto and entrada.canal == "Formulário":
        canal = "E-mail"

    demanda = servico.registrar_demanda(servico.EntradaDemanda(
        canal=canal,
        solicitante=entrada.solicitante,
        email_solicitante=entrada.email_solicitante,
        departamento=entrada.departamento,
        assunto=entrada.assunto,
        descricao=entrada.descricao,
        prazo=entrada.prazo,
        documentos=[Anexo(d.nome, _b64(d.conteudo_base64, d.nome)) for d in entrada.documentos],
        email_bruto=email_bruto,
    ))
    return {"demanda": demanda, "notificacao": servico.montar_notificacao(demanda, "nova_demanda")}


@app.get("/demandas")
def listar_demandas() -> list[dict[str, Any]]:
    return banco.listar_demandas()


@app.get("/demandas/{codigo}")
def obter_demanda(codigo: str) -> dict[str, Any]:
    demanda = banco.obter_demanda_por_codigo(codigo)
    if demanda is None:
        raise HTTPException(404, "Demanda não encontrada")
    return demanda


@app.get("/alertas/pendentes")
def alertas_pendentes() -> dict[str, Any]:
    alertas = servico.alertas_pendentes()
    return {"quantidade": len(alertas), "alertas": alertas}


@app.post("/notificacoes", status_code=201)
def registrar_notificacao(entrada: NotificacaoEntrada) -> dict[str, Any]:
    if banco.obter_demanda(entrada.demanda_id) is None:
        raise HTTPException(404, "Demanda não encontrada")
    nid = servico.registrar_notificacao(entrada.demanda_id, entrada.tipo, entrada.situacao, entrada.destino)
    return {"id": nid}
