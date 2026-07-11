"""Lambda authorizer (HTTP API payload v2, simple response).

Valida o Bearer JWT (HS256, mesmo JWT_SECRET do app), exige ``type=access``
e expiracao valida; devolve ``{"isAuthorized": bool, "context": {...}}``.
"""

from __future__ import annotations

from typing import Any

import jwt as pyjwt

from src.autenticacao_cpf import token

_NEGADO: dict[str, Any] = {"isAuthorized": False, "context": {}}


def lambda_handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    headers = event.get("headers") or {}
    autorizacao = headers.get("authorization") or headers.get("Authorization") or ""
    if not autorizacao.lower().startswith("bearer "):
        return _NEGADO

    try:
        claims = token.validar_access_token(autorizacao[7:])
    except pyjwt.InvalidTokenError:
        return _NEGADO

    if claims.get("type") != "access":
        return _NEGADO

    return {
        "isAuthorized": True,
        "context": {
            "cliente_id": str(claims["sub"]),
            "papel": str(claims.get("papel", "")),
        },
    }
