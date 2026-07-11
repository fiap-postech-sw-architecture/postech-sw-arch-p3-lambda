from __future__ import annotations

import uuid
from types import TracebackType
from typing import Any

import psycopg
import pytest

from src.autenticacao_cpf import db

_ID = uuid.uuid4()


class _FakeCursor:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row
        self.query: str = ""
        self.params: tuple[Any, ...] = ()

    def execute(self, query: str, params: tuple[Any, ...]) -> None:
        self.query = query
        self.params = params

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


class _FakeConn:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self.cursor_obj = _FakeCursor(row)

    def cursor(self) -> _FakeCursor:
        return self.cursor_obj

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


def _patch_connect(
    monkeypatch: pytest.MonkeyPatch, row: tuple[Any, ...] | None
) -> _FakeConn:
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")
    conn = _FakeConn(row)
    monkeypatch.setattr(psycopg, "connect", lambda url: conn)
    return conn


def test_retorna_cliente_quando_hash_existe(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _patch_connect(monkeypatch, (_ID, "c@e.com", True))
    cliente = db.buscar_cliente_por_hash("hash-abc")
    assert cliente == db.Cliente(id=str(_ID), contato="c@e.com", ativo=True)
    assert conn.cursor_obj.params == ("hash-abc",)
    assert "documento_hash = %s" in conn.cursor_obj.query


def test_retorna_none_quando_hash_nao_existe(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_connect(monkeypatch, None)
    assert db.buscar_cliente_por_hash("hash-abc") is None


def test_erro_sem_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db.buscar_cliente_por_hash("hash-abc")
