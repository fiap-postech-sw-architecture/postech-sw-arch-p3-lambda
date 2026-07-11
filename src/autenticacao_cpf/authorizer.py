"""Lambda authorizer (HTTP API payload v2, simple response).

Valida o Bearer JWT (HS256, mesmo JWT_SECRET do app), exige ``type=access``
e expiracao valida; devolve ``{"isAuthorized": bool, "context": {...}}``.
"""

from __future__ import annotations

from typing import Any

import jwt as pyjwt

from src.autenticacao_cpf import logging_json, token

_logger = logging_json.configurar_logger(__name__)


def _negado(motivo: str, request_id: str | None) -> dict[str, Any]:
    # Dict novo por chamada: resposta nunca compartilha estado mutavel.
    _logger.info("Autorizacao negada: %s", motivo, extra={"request_id": request_id})
    return {"isAuthorized": False, "context": {}}


def lambda_handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    # request id da HTTP API (payload v2), quando presente (RNF-029).
    request_id = (event.get("requestContext") or {}).get("requestId")

    headers = event.get("headers") or {}
    autorizacao = headers.get("authorization") or headers.get("Authorization") or ""
    if not autorizacao.lower().startswith("bearer "):
        return _negado("esquema ausente ou nao Bearer", request_id)

    try:
        claims = token.validar_access_token(autorizacao[7:])
    except pyjwt.InvalidTokenError:
        return _negado("token invalido ou expirado", request_id)

    if claims.get("type") != "access":
        return _negado("type diferente de access", request_id)

    return {
        "isAuthorized": True,
        "context": {
            "cliente_id": str(claims["sub"]),
            "papel": str(claims.get("papel", "")),
        },
    }
