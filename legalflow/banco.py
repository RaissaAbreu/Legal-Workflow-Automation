"""Acesso ao SQLite: criação do esquema e consultas."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS responsaveis (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT NOT NULL,
    email         TEXT NOT NULL DEFAULT '',
    area          TEXT NOT NULL,
    teams_webhook TEXT NOT NULL DEFAULT '',
    ativo         INTEGER NOT NULL DEFAULT 1,
    criado_em     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS demandas (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo                TEXT UNIQUE,
    canal                 TEXT NOT NULL,
    solicitante           TEXT NOT NULL DEFAULT '',
    email_solicitante     TEXT NOT NULL DEFAULT '',
    departamento          TEXT NOT NULL DEFAULT '',
    assunto               TEXT NOT NULL DEFAULT '',
    descricao             TEXT NOT NULL DEFAULT '',
    area                  TEXT NOT NULL,
    area_sugerida         TEXT NOT NULL,
    confianca             REAL NOT NULL DEFAULT 0,
    termos_json           TEXT NOT NULL DEFAULT '{}',
    pontuacoes_json       TEXT NOT NULL DEFAULT '{}',
    prioridade            TEXT NOT NULL,
    prioridade_sugerida   TEXT NOT NULL,
    motivos_json          TEXT NOT NULL DEFAULT '[]',
    prazo                 TEXT,
    prazo_origem          TEXT NOT NULL DEFAULT '',
    prazo_a_definir       INTEGER NOT NULL DEFAULT 0,
    prazo_definido_em     TEXT,
    status                TEXT NOT NULL,
    responsavel_id        INTEGER REFERENCES responsaveis(id),
    observacoes           TEXT NOT NULL DEFAULT '',
    motor                 TEXT NOT NULL DEFAULT '',
    recebida_em           TEXT NOT NULL,
    atualizada_em         TEXT NOT NULL,
    concluida_em          TEXT
);

CREATE TABLE IF NOT EXISTS documentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    demanda_id      INTEGER NOT NULL REFERENCES demandas(id) ON DELETE CASCADE,
    nome            TEXT NOT NULL,
    caminho         TEXT NOT NULL,
    tamanho         INTEGER NOT NULL,
    caracteres_texto INTEGER NOT NULL DEFAULT 0,
    criado_em       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historico (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    demanda_id  INTEGER NOT NULL REFERENCES demandas(id) ON DELETE CASCADE,
    evento      TEXT NOT NULL,
    detalhe     TEXT NOT NULL DEFAULT '',
    autor       TEXT NOT NULL DEFAULT 'Automação',
    criado_em   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notificacoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    demanda_id  INTEGER NOT NULL REFERENCES demandas(id) ON DELETE CASCADE,
    tipo        TEXT NOT NULL,
    canal       TEXT NOT NULL DEFAULT 'Microsoft Teams',
    destino     TEXT NOT NULL DEFAULT '',
    situacao    TEXT NOT NULL,
    criado_em   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_demandas_status ON demandas(status);
CREATE INDEX IF NOT EXISTS ix_demandas_prazo ON demandas(prazo);
CREATE INDEX IF NOT EXISTS ix_notificacoes_demanda ON notificacoes(demanda_id, tipo);
"""

CAMPOS_JSON = {"termos_json": "termos", "pontuacoes_json": "pontuacoes", "motivos_json": "motivos"}


def agora_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


@contextmanager
def conexao() -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(config.caminho_banco(), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def inicializar() -> None:
    with conexao() as con:
        con.executescript(ESQUEMA)


def _demanda_para_dict(linha: sqlite3.Row) -> dict[str, Any]:
    d = dict(linha)
    for coluna, chave in CAMPOS_JSON.items():
        d[chave] = json.loads(d.pop(coluna) or "null")
    d["prazo_a_definir"] = bool(d["prazo_a_definir"])
    return d


SELECT_DEMANDA = """
SELECT d.*, r.nome AS responsavel_nome, r.email AS responsavel_email,
       r.teams_webhook AS responsavel_teams_webhook,
       (SELECT COUNT(*) FROM documentos doc WHERE doc.demanda_id = d.id) AS qtd_documentos
FROM demandas d LEFT JOIN responsaveis r ON r.id = d.responsavel_id
"""


# --------------------------------------------------------------------------- demandas


def inserir_demanda(dados: dict[str, Any]) -> int:
    registro = dict(dados)
    for coluna, chave in CAMPOS_JSON.items():
        registro[coluna] = json.dumps(registro.pop(chave, None), ensure_ascii=False)
    registro["prazo_a_definir"] = int(bool(registro.get("prazo_a_definir")))
    colunas = ", ".join(registro)
    marcadores = ", ".join(f":{c}" for c in registro)
    with conexao() as con:
        cur = con.execute(f"INSERT INTO demandas ({colunas}) VALUES ({marcadores})", registro)
        demanda_id = cur.lastrowid
        con.execute("UPDATE demandas SET codigo = ? WHERE id = ?", (f"DEM-{demanda_id:04d}", demanda_id))
    return demanda_id


def atualizar_demanda(demanda_id: int, campos: dict[str, Any]) -> None:
    if not campos:
        return
    campos = dict(campos)
    if "prazo_a_definir" in campos:
        campos["prazo_a_definir"] = int(bool(campos["prazo_a_definir"]))
    campos["atualizada_em"] = agora_iso()
    atribuicoes = ", ".join(f"{c} = :{c}" for c in campos)
    with conexao() as con:
        con.execute(f"UPDATE demandas SET {atribuicoes} WHERE id = :id", {**campos, "id": demanda_id})


def obter_demanda(demanda_id: int) -> dict[str, Any] | None:
    with conexao() as con:
        linha = con.execute(SELECT_DEMANDA + " WHERE d.id = ?", (demanda_id,)).fetchone()
    return _demanda_para_dict(linha) if linha else None


def obter_demanda_por_codigo(codigo: str) -> dict[str, Any] | None:
    with conexao() as con:
        linha = con.execute(SELECT_DEMANDA + " WHERE d.codigo = ?", (codigo.upper(),)).fetchone()
    return _demanda_para_dict(linha) if linha else None


def listar_demandas() -> list[dict[str, Any]]:
    with conexao() as con:
        linhas = con.execute(SELECT_DEMANDA + " ORDER BY d.id DESC").fetchall()
    return [_demanda_para_dict(linha) for linha in linhas]


def contar_demandas() -> int:
    with conexao() as con:
        return con.execute("SELECT COUNT(*) FROM demandas").fetchone()[0]


# --------------------------------------------------------------------------- documentos


def inserir_documento(demanda_id: int, nome: str, caminho: str, tamanho: int, caracteres: int) -> None:
    with conexao() as con:
        con.execute(
            "INSERT INTO documentos (demanda_id, nome, caminho, tamanho, caracteres_texto, criado_em)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (demanda_id, nome, caminho, tamanho, caracteres, agora_iso()),
        )


def listar_documentos(demanda_id: int) -> list[dict[str, Any]]:
    with conexao() as con:
        linhas = con.execute("SELECT * FROM documentos WHERE demanda_id = ? ORDER BY id", (demanda_id,)).fetchall()
    return [dict(linha) for linha in linhas]


# --------------------------------------------------------------------------- histórico


def registrar_historico(demanda_id: int, evento: str, detalhe: str = "", autor: str = "Automação") -> None:
    with conexao() as con:
        con.execute(
            "INSERT INTO historico (demanda_id, evento, detalhe, autor, criado_em) VALUES (?, ?, ?, ?, ?)",
            (demanda_id, evento, detalhe, autor, agora_iso()),
        )


def listar_historico(demanda_id: int) -> list[dict[str, Any]]:
    with conexao() as con:
        linhas = con.execute("SELECT * FROM historico WHERE demanda_id = ? ORDER BY id DESC", (demanda_id,)).fetchall()
    return [dict(linha) for linha in linhas]


# --------------------------------------------------------------------------- notificações


def inserir_notificacao(demanda_id: int, tipo: str, situacao: str, destino: str = "") -> int:
    with conexao() as con:
        cur = con.execute(
            "INSERT INTO notificacoes (demanda_id, tipo, destino, situacao, criado_em) VALUES (?, ?, ?, ?, ?)",
            (demanda_id, tipo, destino, situacao, agora_iso()),
        )
        return cur.lastrowid


def listar_notificacoes(demanda_id: int | None = None) -> list[dict[str, Any]]:
    sql = (
        "SELECT n.*, d.codigo, d.assunto FROM notificacoes n JOIN demandas d ON d.id = n.demanda_id"
    )
    params: tuple = ()
    if demanda_id is not None:
        sql += " WHERE n.demanda_id = ?"
        params = (demanda_id,)
    with conexao() as con:
        linhas = con.execute(sql + " ORDER BY n.id DESC", params).fetchall()
    return [dict(linha) for linha in linhas]


def ultima_notificacao(demanda_id: int, tipo: str) -> str | None:
    with conexao() as con:
        linha = con.execute(
            "SELECT MAX(criado_em) FROM notificacoes WHERE demanda_id = ? AND tipo = ?", (demanda_id, tipo)
        ).fetchone()
    return linha[0] if linha else None


# --------------------------------------------------------------------------- responsáveis


def listar_responsaveis(apenas_ativos: bool = False) -> list[dict[str, Any]]:
    sql = """
    SELECT r.*, (SELECT COUNT(*) FROM demandas d WHERE d.responsavel_id = r.id
                 AND d.status NOT IN ('Concluída', 'Cancelada')) AS demandas_abertas
    FROM responsaveis r
    """
    if apenas_ativos:
        sql += " WHERE r.ativo = 1"
    with conexao() as con:
        linhas = con.execute(sql + " ORDER BY r.area, r.nome").fetchall()
    return [dict(linha) for linha in linhas]


def inserir_responsavel(nome: str, email: str, area: str, teams_webhook: str = "", ativo: bool = True) -> int:
    with conexao() as con:
        cur = con.execute(
            "INSERT INTO responsaveis (nome, email, area, teams_webhook, ativo, criado_em) VALUES (?, ?, ?, ?, ?, ?)",
            (nome.strip(), email.strip(), area, teams_webhook.strip(), int(ativo), agora_iso()),
        )
        return cur.lastrowid


def atualizar_responsavel(responsavel_id: int, **campos: Any) -> None:
    if "ativo" in campos:
        campos["ativo"] = int(bool(campos["ativo"]))
    atribuicoes = ", ".join(f"{c} = :{c}" for c in campos)
    with conexao() as con:
        con.execute(f"UPDATE responsaveis SET {atribuicoes} WHERE id = :id", {**campos, "id": responsavel_id})


def excluir_responsavel(responsavel_id: int) -> None:
    with conexao() as con:
        con.execute("UPDATE demandas SET responsavel_id = NULL WHERE responsavel_id = ?", (responsavel_id,))
        con.execute("DELETE FROM responsaveis WHERE id = ?", (responsavel_id,))


def obter_responsavel(responsavel_id: int) -> dict[str, Any] | None:
    with conexao() as con:
        linha = con.execute("SELECT * FROM responsaveis WHERE id = ?", (responsavel_id,)).fetchone()
    return dict(linha) if linha else None
