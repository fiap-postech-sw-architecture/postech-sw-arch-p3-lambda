from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt

from src.autenticacao_cpf import authorizer, token


def _evento(header: str | None) -> dict[str, Any]:
    return {"headers": {"authorization": header} if header is not None else {}}


def _token(**overrides: Any) -> str:
    secret = overrides.pop("_secret", "segredo-teste-lambda")
    agora = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": "cliente-1",
        "papel": "cliente",
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": agora,
        "exp": agora + timedelta(minutes=5),
    }
    payload.update(overrides)
    return pyjwt.encode(payload, secret, algorithm="HS256")


def test_autoriza_token_valido() -> None:
    gerado = token.emitir_access_token("cliente-1", "c@e.com")
    resultado = authorizer.lambda_handler(_evento(f"Bearer {gerado}"), None)
    assert resultado["isAuthorized"] is True
    assert resultado["context"] == {"cliente_id": "cliente-1", "papel": "cliente"}


def test_nega_sem_header() -> None:
    assert authorizer.lambda_handler({}, None)["isAuthorized"] is False
    assert authorizer.lambda_handler(_evento(None), None)["isAuthorized"] is False


def test_nega_esquema_nao_bearer() -> None:
    resultado = authorizer.lambda_handler(_evento("Basic abc"), None)
    assert resultado["isAuthorized"] is False


def test_nega_assinatura_invalida() -> None:
    forjado = _token(_secret="segredo-errado")
    resultado = authorizer.lambda_handler(_evento(f"Bearer {forjado}"), None)
    assert resultado["isAuthorized"] is False


def test_nega_token_expirado() -> None:
    expirado = _token(exp=datetime.now(UTC) - timedelta(minutes=1))
    resultado = authorizer.lambda_handler(_evento(f"Bearer {expirado}"), None)
    assert resultado["isAuthorized"] is False


def test_nega_type_diferente_de_access() -> None:
    refresh = _token(type="refresh")
    resultado = authorizer.lambda_handler(_evento(f"Bearer {refresh}"), None)
    assert resultado["isAuthorized"] is False


def test_aceita_header_capitalizado() -> None:
    gerado = token.emitir_access_token("cliente-1", "c@e.com")
    evento = {"headers": {"Authorization": f"Bearer {gerado}"}}
    assert authorizer.lambda_handler(evento, None)["isAuthorized"] is True
