"""Emissao de JWT com os mesmos claims estruturais do app principal.

Paridade com ``src/autenticacao/infraestrutura/jwt_service.py`` do app:
claims ``sub``, ``email``, ``papel``, ``type``, ``jti``, ``iat``, ``exp``,
algoritmo HS256 com ``JWT_SECRET``. Aqui sempre ``papel="cliente"`` e
``type="access"`` -- o authorizer do app valida esses tokens sem mudanca.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from src.autenticacao_cpf import env_obrigatoria

ALGORITMO = "HS256"

# Cold start: JWT_SECRET ausente aborta o boot (sem default inseguro).
_JWT_SECRET = env_obrigatoria("JWT_SECRET")
EXPIRACAO_MINUTOS = int(os.environ.get("JWT_EXPIRATION_MINUTES", "30"))


def emitir_access_token(cliente_id: str, contato: str) -> str:
    """Gera o access token do cliente autenticado por CPF."""
    agora = datetime.now(UTC)
    payload = {
        "sub": cliente_id,
        # `contato` e texto livre (pode ser telefone): PII nao entra num claim
        # chamado `email` -- so vai se de fato parecer email.
        "email": contato if "@" in contato else "",
        "papel": "cliente",
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": agora,
        "exp": agora + timedelta(minutes=EXPIRACAO_MINUTOS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=ALGORITMO)


def validar_access_token(token: str) -> dict[str, object]:
    """Decodifica e valida assinatura/expiracao; jwt.InvalidTokenError se invalido."""
    return jwt.decode(
        token,
        _JWT_SECRET,
        algorithms=[ALGORITMO],
        options={"require": ["sub", "jti", "exp", "type"]},
    )
