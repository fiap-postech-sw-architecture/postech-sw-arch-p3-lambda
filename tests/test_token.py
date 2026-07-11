from __future__ import annotations

import importlib
import json
import os

import jwt as pyjwt
import pytest

from src.autenticacao_cpf import token


def test_round_trip_claims_estruturais() -> None:
    gerado = token.emitir_access_token("cliente-123", "cli@ex.com")
    claims = pyjwt.decode(
        gerado,
        os.environ["JWT_SECRET"],
        algorithms=["HS256"],
        options={"require": ["sub", "jti", "exp", "type"]},
    )
    assert claims["sub"] == "cliente-123"
    assert claims["email"] == "cli@ex.com"
    assert claims["papel"] == "cliente"
    assert claims["type"] == "access"
    assert claims["exp"] - claims["iat"] == token.EXPIRACAO_MINUTOS * 60
    assert claims["jti"]


def test_email_vazio_quando_contato_nao_e_email() -> None:
    # contato e texto livre (pode ser telefone): PII nao entra no claim `email`.
    gerado = token.emitir_access_token("cliente-123", "11 99999-0000")
    claims = pyjwt.decode(gerado, os.environ["JWT_SECRET"], algorithms=["HS256"])
    assert claims["email"] == ""
    assert "99999" not in json.dumps(claims)


def test_validar_access_token_rejeita_assinatura_errada() -> None:
    forjado = pyjwt.encode({"sub": "x"}, "outro-segredo", algorithm="HS256")
    with pytest.raises(pyjwt.InvalidTokenError):
        token.validar_access_token(forjado)


def test_cold_start_sem_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        importlib.reload(token)
    monkeypatch.undo()
    importlib.reload(token)
