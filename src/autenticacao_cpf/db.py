"""Consulta de cliente por documento_hash no PostgreSQL do app.

Tabela e colunas conforme ``src/cliente_veiculo/infraestrutura/mapping.py``
do app principal: ``clientes(id, contato, ativo, documento_hash unique)``.
"""

from __future__ import annotations

from typing import NamedTuple

import psycopg

from src.autenticacao_cpf import env_obrigatoria


class Cliente(NamedTuple):
    id: str
    contato: str
    ativo: bool


def buscar_cliente_por_hash(documento_hash: str) -> Cliente | None:
    """Busca o cliente pelo hash deterministico do documento; None se nao existir."""
    # ponytail: conexao por invocacao; pool/keep-alive se a latencia incomodar
    database_url = env_obrigatoria("DATABASE_URL")
    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, contato, ativo FROM clientes WHERE documento_hash = %s",
            (documento_hash,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return Cliente(id=str(row[0]), contato=str(row[1]), ativo=bool(row[2]))
