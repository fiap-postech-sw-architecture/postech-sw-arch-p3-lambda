"""Integracao real com PostgreSQL via testcontainers (exige Docker).

Fora do gate default (marker ``integration``); rode com ``make test-integ``.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import psycopg
import pytest

from src.autenticacao_cpf import db, hashing

pytestmark = pytest.mark.integration

CPF = "52998224725"

_DDL = """
CREATE TABLE clientes (
    id UUID PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    documento VARCHAR(255) NOT NULL,
    documento_hash VARCHAR(64) NOT NULL UNIQUE,
    tipo_documento VARCHAR(4) NOT NULL,
    contato VARCHAR(255) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
)
"""


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver=None) as pg:
        yield pg.get_connection_url()


@pytest.fixture()
def banco_populado(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> Iterator[dict[str, str]]:
    monkeypatch.setenv("DATABASE_URL", database_url)
    ativo_id, inativo_id = str(uuid.uuid4()), str(uuid.uuid4())
    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute(_DDL)
        cur.execute(
            "INSERT INTO clientes VALUES (%s, 'Ana', 'enc', %s, 'cpf', %s, TRUE)",
            (ativo_id, hashing.hash_documento(CPF), "ana@ex.com"),
        )
        cur.execute(
            "INSERT INTO clientes VALUES (%s, 'Ines', 'enc2', %s, 'cpf', %s, FALSE)",
            (inativo_id, hashing.hash_documento("11144477735"), "ines@ex.com"),
        )
    yield {"ativo": ativo_id, "inativo": inativo_id}
    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute("DROP TABLE clientes")


def test_busca_por_hash_encontra_cliente_ativo(banco_populado: dict[str, str]) -> None:
    cliente = db.buscar_cliente_por_hash(hashing.hash_documento(CPF))
    assert cliente is not None
    assert cliente.id == banco_populado["ativo"]
    assert cliente.contato == "ana@ex.com"
    assert cliente.ativo is True


def test_busca_por_hash_cliente_inativo(banco_populado: dict[str, str]) -> None:
    cliente = db.buscar_cliente_por_hash(hashing.hash_documento("11144477735"))
    assert cliente is not None
    assert cliente.ativo is False


def test_busca_por_hash_inexistente(banco_populado: dict[str, str]) -> None:
    assert db.buscar_cliente_por_hash("0" * 64) is None
