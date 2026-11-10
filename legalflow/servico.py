"""Regras de negócio: registrar, classificar, encaminhar, triar e monitorar demandas."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from . import banco, config
from .classificacao import classificar
from .constantes import (
    AREA_NAO_CLASSIFICADA,
    CONFIANCA_MINIMA_ENCAMINHAMENTO,
    STATUS_FINAIS,
    TIPOS_NOTIFICACAO,
)
from .extracao import (
    Anexo,
    extrair_departamento,
    extrair_email,
    extrair_prazo,
    extrair_solicitante,
    extrair_texto_documento,
    ler_email,
)
from .prioridade import sugerir_prioridade
from .texto import resumir


@dataclass
class EntradaDemanda:
    """Dados de entrada vindos do formulário, do e-mail (via n8n) ou do painel."""

    canal: str = "Formulário"
    solicitante: str = ""
    email_solicitante: str = ""
    departamento: str = ""
    assunto: str = ""
    descricao: str = ""
    prazo: date | None = None  # prazo informado explicitamente no formulário
    documentos: list[Anexo] = field(default_factory=list)
    email_bruto: bytes | None = None  # conteúdo .eml completo, quando a entrada é um e-mail
    recebida_em: datetime | None = None


# --------------------------------------------------------------------------- utilitários


def _nome_seguro(nome: str) -> str:
    nome = Path(nome).name
    return re.sub(r"[^\w.\- ]", "_", nome).strip() or "documento"


def _hoje() -> date:
    return date.today()


def escolher_responsavel(area: str) -> dict[str, Any] | None:
    """Responsável ativo da área com menos demandas em aberto."""
    candidatos = [r for r in banco.listar_responsaveis(apenas_ativos=True) if r["area"] == area]
    if not candidatos:
        return None
    return min(candidatos, key=lambda r: (r["demandas_abertas"], r["id"]))


def destino_teams(demanda: dict[str, Any]) -> str:
    return (demanda.get("responsavel_teams_webhook") or "").strip() or config.teams_webhook_padrao()


def formatar_data(valor: str | date | None) -> str:
    if not valor:
        return "—"
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor)
    return valor.strftime("%d/%m/%Y")


def dias_ate_prazo(demanda: dict[str, Any], hoje: date | None = None) -> int | None:
    if not demanda.get("prazo"):
        return None
    return (date.fromisoformat(demanda["prazo"]) - (hoje or _hoje())).days


def situacao_prazo(demanda: dict[str, Any], hoje: date | None = None) -> str:
    """'vencida', 'vence_hoje', 'vence_em_breve', 'no_prazo', 'prazo_a_definir' ou 'encerrada'."""
    if demanda["status"] in STATUS_FINAIS:
        return "encerrada"
    dias = dias_ate_prazo(demanda, hoje)
    if dias is None:
        return "prazo_a_definir"
    if dias < 0:
        return "vencida"
    if dias == 0:
        return "vence_hoje"
    if dias <= config.dias_alerta_proximo():
        return "vence_em_breve"
    return "no_prazo"


# --------------------------------------------------------------------------- registro


def registrar_demanda(entrada: EntradaDemanda) -> dict[str, Any]:
    """Fluxo completo: extrai, classifica, prioriza, registra, encaminha. Devolve a demanda."""
    banco.inicializar()
    recebida_em = (entrada.recebida_em or datetime.now()).replace(microsecond=0)
    documentos = list(entrada.documentos)

    solicitante, email_solicitante = entrada.solicitante, entrada.email_solicitante
    assunto, descricao = entrada.assunto, entrada.descricao

    if entrada.email_bruto:
        lido = ler_email(entrada.email_bruto)
        solicitante = solicitante or lido.remetente_nome or lido.remetente_email
        email_solicitante = email_solicitante or lido.remetente_email
        assunto = assunto or lido.assunto
        descricao = descricao or lido.corpo
        documentos.extend(lido.anexos)
        if lido.data and not entrada.recebida_em:
            recebida_em = lido.data.astimezone().replace(tzinfo=None, microsecond=0)

    textos_documentos = [(doc, extrair_texto_documento(doc.nome, doc.conteudo)) for doc in documentos]
    texto_completo = "\n".join([assunto, descricao, *(t for _, t in textos_documentos)])

    solicitante = solicitante or extrair_solicitante(texto_completo)
    email_solicitante = email_solicitante or extrair_email(descricao)
    departamento = entrada.departamento or extrair_departamento(texto_completo)

    # Prazo: o informado no formulário prevalece; senão, procura no texto.
    prazo, prazo_origem = entrada.prazo, "Informado pelo solicitante" if entrada.prazo else ""
    if prazo is None:
        # primeiro o assunto e o corpo; os anexos só se a mensagem não citar prazo
        for origem, texto in (("texto", f"{assunto}\n{descricao}"),
                              ("documentos", "\n".join(t for _, t in textos_documentos))):
            achado = extrair_prazo(texto, recebida_em.date())
            if achado:
                prazo, prazo_origem = achado.data, f"Extraído do {origem}: “{achado.trecho}”"
                break

    classificacao = classificar(texto_completo)
    prioridade = sugerir_prioridade(texto_completo, prazo, _hoje())

    responsavel = None
    if classificacao.area != AREA_NAO_CLASSIFICADA:
        responsavel = escolher_responsavel(classificacao.area)
    encaminhar = responsavel is not None and classificacao.confianca >= CONFIANCA_MINIMA_ENCAMINHAMENTO
    status = "Encaminhada" if encaminhar else "Em triagem"

    agora = banco.agora_iso()
    demanda_id = banco.inserir_demanda({
        "canal": entrada.canal,
        "solicitante": solicitante or "Não identificado",
        "email_solicitante": email_solicitante,
        "departamento": departamento,
        "assunto": assunto or resumir(descricao, 80) or "(sem assunto)",
        "descricao": descricao,
        "area": classificacao.area,
        "area_sugerida": classificacao.area,
        "confianca": classificacao.confianca,
        "termos": classificacao.termos,
        "pontuacoes": classificacao.pontuacoes,
        "prioridade": prioridade.prioridade,
        "prioridade_sugerida": prioridade.prioridade,
        "motivos": prioridade.motivos,
        "prazo": prazo.isoformat() if prazo else None,
        "prazo_origem": prazo_origem,
        "prazo_a_definir": prioridade.prazo_a_definir,
        "prazo_definido_em": agora,
        "status": status,
        "responsavel_id": responsavel["id"] if responsavel else None,
        "motor": classificacao.motor,
        "recebida_em": recebida_em.isoformat(),
        "atualizada_em": agora,
    })

    codigo = f"DEM-{demanda_id:04d}"
    pasta = config.dir_documentos() / codigo
    for doc, texto in textos_documentos:
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / _nome_seguro(doc.nome)
        destino.write_bytes(doc.conteudo)
        banco.inserir_documento(demanda_id, doc.nome, str(destino), len(doc.conteudo), len(texto.strip()))

    banco.registrar_historico(demanda_id, "Recebida", f"Canal: {entrada.canal} · {len(documentos)} documento(s)")
    banco.registrar_historico(
        demanda_id, "Classificada",
        f"{classificacao.area} (confiança {classificacao.confianca:.0%}) · prioridade {prioridade.prioridade}",
    )
    if encaminhar:
        banco.registrar_historico(demanda_id, "Encaminhada", f"Para {responsavel['nome']}")
    else:
        motivo = ("sem responsável cadastrado para a área" if responsavel is None and
                  classificacao.area != AREA_NAO_CLASSIFICADA else
                  "classificação com baixa confiança" if classificacao.area != AREA_NAO_CLASSIFICADA else
                  "área não identificada")
        banco.registrar_historico(demanda_id, "Enviada para triagem", motivo.capitalize())

    return banco.obter_demanda(demanda_id)


# --------------------------------------------------------------------------- triagem


ROTULOS_CAMPOS = {
    "area": "Área", "prioridade": "Prioridade", "prazo": "Prazo", "status": "Status",
    "responsavel_id": "Responsável", "observacoes": "Observações", "prazo_a_definir": "Prazo a definir",
}


def atualizar_triagem(demanda_id: int, alteracoes: dict[str, Any], autor: str = "Analista") -> list[str]:
    """Aplica as correções do analista e registra cada mudança no histórico."""
    atual = banco.obter_demanda(demanda_id)
    if atual is None:
        raise ValueError("Demanda não encontrada")

    if "prazo" in alteracoes:
        prazo = alteracoes["prazo"]
        alteracoes["prazo"] = prazo.isoformat() if isinstance(prazo, date) else (prazo or None)
        alteracoes["prazo_a_definir"] = alteracoes["prazo"] is None
        if alteracoes["prazo"] != atual["prazo"]:
            alteracoes["prazo_origem"] = f"Definido por {autor}" if alteracoes["prazo"] else ""
            alteracoes["prazo_definido_em"] = banco.agora_iso()  # reabre os alertas de prazo
    mudancas = {c: v for c, v in alteracoes.items() if atual.get(c) != v}
    if not mudancas:
        return []

    if mudancas.get("status") in STATUS_FINAIS:
        mudancas["concluida_em"] = banco.agora_iso()
    elif "status" in mudancas:
        mudancas["concluida_em"] = None

    banco.atualizar_demanda(demanda_id, mudancas)

    descricoes = []
    for campo, novo in mudancas.items():
        if campo not in ROTULOS_CAMPOS or campo == "prazo_a_definir":
            continue
        antigo = atual.get(campo)
        if campo == "responsavel_id":
            antigo = atual.get("responsavel_nome") or "—"
            r = banco.obter_responsavel(novo) if novo else None
            novo = r["nome"] if r else "—"
        elif campo == "prazo":
            antigo, novo = formatar_data(antigo), formatar_data(novo)
        elif campo == "observacoes":
            antigo, novo = "", resumir(novo, 120)
        texto = f"{ROTULOS_CAMPOS[campo]}: {antigo or '—'} → {novo or '—'}" if antigo else f"{ROTULOS_CAMPOS[campo]}: {novo}"
        descricoes.append(texto)
        banco.registrar_historico(demanda_id, "Triagem", texto, autor)
    return descricoes


# --------------------------------------------------------------------------- notificações (Teams)


CORES_PRIORIDADE = {"Crítica": "Attention", "Alta": "Warning", "Média": "Accent", "Baixa": "Default"}

TITULOS_ALERTA = {
    "nova_demanda": "Nova demanda jurídica",
    "vencida": "Prazo vencido",
    "vence_hoje": "Prazo vence hoje",
    "vence_em_breve": "Prazo próximo do vencimento",
    "prazo_a_definir": "Demanda sem prazo definido",
}


def montar_payload_teams(demanda: dict[str, Any], tipo: str) -> dict[str, Any]:
    """Mensagem no formato Adaptive Card, aceito pelos webhooks do Teams (Workflows)."""
    dias = dias_ate_prazo(demanda)
    if dias is None:
        prazo_txt = "A definir"
    elif dias < 0:
        prazo_txt = f"{formatar_data(demanda['prazo'])} (vencido há {-dias} dia(s))"
    elif dias == 0:
        prazo_txt = f"{formatar_data(demanda['prazo'])} (hoje)"
    else:
        prazo_txt = f"{formatar_data(demanda['prazo'])} (em {dias} dia(s))"

    link = f"{config.url_painel()}/?demanda={demanda['codigo']}"
    cartao = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {"type": "TextBlock", "text": "LEGAL FLOW", "size": "Small", "weight": "Bolder",
             "color": "Accent", "spacing": "None"},
            {"type": "TextBlock", "text": f"{TITULOS_ALERTA.get(tipo, 'Alerta')} · {demanda['codigo']}",
             "size": "Large", "weight": "Bolder", "wrap": True,
             "color": CORES_PRIORIDADE.get(demanda["prioridade"], "Default")},
            {"type": "TextBlock", "text": demanda["assunto"], "wrap": True, "spacing": "Small"},
            {"type": "FactSet", "facts": [
                {"title": "Área", "value": demanda["area"]},
                {"title": "Prioridade", "value": demanda["prioridade"]},
                {"title": "Prazo", "value": prazo_txt},
                {"title": "Solicitante", "value": f"{demanda['solicitante']}"
                                                  + (f" · {demanda['departamento']}" if demanda["departamento"] else "")},
                {"title": "Responsável", "value": demanda.get("responsavel_nome") or "Sem responsável (triagem)"},
                {"title": "Status", "value": demanda["status"]},
            ]},
            {"type": "TextBlock", "text": "Classificação preliminar automática; requer validação humana.",
             "size": "Small", "isSubtle": True, "wrap": True},
        ],
        "actions": [{"type": "Action.OpenUrl", "title": "Abrir no painel", "url": link}],
    }
    return {
        "type": "message",
        "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "contentUrl": None,
                         "content": cartao}],
    }


def montar_notificacao(demanda: dict[str, Any], tipo: str) -> dict[str, Any]:
    """Pacote que o n8n usa: para onde enviar, o que enviar e como registrar depois."""
    return {
        "demanda_id": demanda["id"],
        "codigo": demanda["codigo"],
        "tipo": tipo,
        "tipo_descricao": TIPOS_NOTIFICACAO[tipo],
        "webhook_url": destino_teams(demanda),
        "destinatario": demanda.get("responsavel_nome") or "Canal padrão",
        "payload": montar_payload_teams(demanda, tipo),
    }


def registrar_notificacao(demanda_id: int, tipo: str, situacao: str, destino: str = "") -> int:
    if tipo not in TIPOS_NOTIFICACAO:
        raise ValueError(f"Tipo de notificação inválido: {tipo}")
    nid = banco.inserir_notificacao(demanda_id, tipo, situacao, destino)
    rotulo = {"enviada": "enviada", "sem_canal": "não enviada (sem canal configurado)", "falha": "falhou"}
    banco.registrar_historico(
        demanda_id, "Notificação", f"{TIPOS_NOTIFICACAO[tipo]} — {rotulo.get(situacao, situacao)}", "n8n"
    )
    return nid


def alertas_pendentes(agora: datetime | None = None) -> list[dict[str, Any]]:
    """Alertas de prazo que ainda não foram enviados (o n8n consulta de hora em hora).

    - vencida: repete a cada N horas (padrão 24h) enquanto a demanda estiver aberta;
    - vence_hoje / vence_em_breve: uma vez por demanda e por data de prazo;
    - prazo_a_definir: uma vez, se a demanda está sem prazo há mais de N horas (padrão 24h).
    """
    banco.inicializar()
    agora = agora or datetime.now()
    hoje = agora.date()
    alertas = []
    for demanda in banco.listar_demandas():
        situacao = situacao_prazo(demanda, hoje)
        if situacao in ("encerrada", "no_prazo"):
            continue
        ultima = banco.ultima_notificacao(demanda["id"], situacao)
        ultima_dt = datetime.fromisoformat(ultima) if ultima else None

        if situacao == "vencida":
            devido = ultima_dt is None or agora - ultima_dt >= timedelta(hours=config.horas_repeticao_vencida())
        elif situacao == "prazo_a_definir":
            recebida = datetime.fromisoformat(demanda["recebida_em"])
            devido = ultima_dt is None and agora - recebida >= timedelta(hours=config.horas_alerta_prazo_a_definir())
        else:
            # enviado uma vez; se o prazo for alterado depois do envio, avisa de novo
            definido = demanda.get("prazo_definido_em") or demanda["recebida_em"]
            devido = ultima_dt is None or ultima_dt < datetime.fromisoformat(definido)
        if devido:
            alertas.append(montar_notificacao(demanda, situacao))
    return alertas


# --------------------------------------------------------------------------- indicadores


def indicadores(hoje: date | None = None) -> dict[str, Any]:
    demandas = banco.listar_demandas()
    abertas = [d for d in demandas if d["status"] not in STATUS_FINAIS]
    situacoes = [situacao_prazo(d, hoje) for d in abertas]
    return {
        "total": len(demandas),
        "abertas": len(abertas),
        "vencidas": situacoes.count("vencida"),
        "vencem_breve": situacoes.count("vence_hoje") + situacoes.count("vence_em_breve"),
        "prazo_a_definir": situacoes.count("prazo_a_definir"),
        "em_triagem": sum(1 for d in abertas if d["status"] in ("Nova", "Em triagem")),
        "concluidas": sum(1 for d in demandas if d["status"] == "Concluída"),
    }
