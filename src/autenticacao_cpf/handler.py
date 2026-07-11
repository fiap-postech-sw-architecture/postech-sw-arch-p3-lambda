"""Handler do POST /auth: valida CPF, consulta cliente e emite JWT."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from brutils.cpf import is_valid

from src.autenticacao_cpf import db, hashing, token

_logger = logging.getLogger(__name__)


def _resposta(status: int, corpo: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(corpo),
    }


def _extrair_cpf(event: dict[str, Any]) -> str | None:
    corpo_bruto = event.get("body") or ""
    if event.get("isBase64Encoded"):
        corpo_bruto = base64.b64decode(corpo_bruto).decode()
    try:
        corpo = json.loads(corpo_bruto)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(corpo, dict) or not isinstance(corpo.get("cpf"), str):
        return None
    return str(corpo["cpf"])


def lambda_handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    cpf_bruto = _extrair_cpf(event)
    if cpf_bruto is None:
        return _resposta(400, {"detail": "Corpo invalido: esperado JSON com campo cpf"})

    cpf = hashing.normalizar_documento(cpf_bruto)
    if not is_valid(cpf):
        return _resposta(400, {"detail": "CPF invalido"})

    cliente = db.buscar_cliente_por_hash(hashing.hash_documento(cpf))
    # Anti-enumeracao: inexistente e inativo recebem a MESMA resposta 401,
    # sem revelar qual condicao falhou.
    if cliente is None or not cliente.ativo:
        _logger.info("Autenticacao negada para CPF nao autorizado")
        return _resposta(401, {"detail": "Credenciais invalidas"})

    access_token = token.emitir_access_token(cliente.id, cliente.contato)
    return _resposta(
        200,
        {
            "access_token": access_token,
            "token_type": "bearer",  # nosec B105 - tipo do token, nao senha
            "expires_in": token.EXPIRACAO_MINUTOS * 60,
        },
    )
