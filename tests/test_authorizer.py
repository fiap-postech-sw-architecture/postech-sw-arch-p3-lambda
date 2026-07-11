from __future__ import annotations

import io
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt

from src.autenticacao_cpf import authorizer, logging_json, token


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


def test_negado_devolve_dict_novo_por_chamada() -> None:
    primeiro = authorizer.lambda_handler({}, None)
    primeiro["context"]["poluido"] = "x"
    segundo = authorizer.lambda_handler({}, None)
    assert primeiro is not segundo
    assert segundo["context"] == {}


def test_log_json_com_request_id() -> None:
    """RNF-029: negacao logada em JSON parseavel com request_id do evento."""
    buf = io.StringIO()
    captura = logging.StreamHandler(buf)
    captura.setFormatter(logging_json.JsonFormatter())
    authorizer._logger.addHandler(captura)
    try:
        evento = {"headers": {}, "requestContext": {"requestId": "req-aut-9"}}
        authorizer.lambda_handler(evento, None)
    finally:
        authorizer._logger.removeHandler(captura)

    linha = json.loads(buf.getvalue().strip())
    assert linha["level"] == "INFO"
    assert linha["request_id"] == "req-aut-9"
    assert "Autorizacao negada" in linha["message"]
