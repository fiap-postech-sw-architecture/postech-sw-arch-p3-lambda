"""Handler do POST /auth: valida CPF, consulta cliente e emite JWT."""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from brutils.cpf import is_valid

from src.autenticacao_cpf import db, hashing, logging_json, token

_logger = logging_json.configurar_logger(__name__)


def _resposta(
    status: int, corpo: dict[str, Any], headers: dict[str, str] | None = None
) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **(headers or {})},
        "body": json.dumps(corpo),
    }


def _extrair_cpf(event: dict[str, Any]) -> str | None:
    corpo_bruto = event.get("body") or ""
    # Toda a borda de parse (base64 -> UTF-8 -> JSON) dentro do try: entrada
    # malformada e sempre 400 do cliente, nunca 500 acionavel.
    try:
        if event.get("isBase64Encoded"):
            corpo_bruto = base64.b64decode(corpo_bruto).decode()
        corpo = json.loads(corpo_bruto)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(corpo, dict) or not isinstance(corpo.get("cpf"), str):
        return None
    return str(corpo["cpf"])


def lambda_handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    # request id da HTTP API (payload v2), quando presente (RNF-029).
    request_id = (event.get("requestContext") or {}).get("requestId")

    cpf_bruto = _extrair_cpf(event)
    if cpf_bruto is None:
        return _resposta(400, {"detail": "Corpo invalido: esperado JSON com campo cpf"})

    cpf = hashing.normalizar_documento(cpf_bruto)
    if not is_valid(cpf):
        return _resposta(400, {"detail": "CPF invalido"})

    cliente = db.buscar_cliente_por_hash(hashing.hash_documento(cpf))
    # Anti-enumeracao: inexistente e inativo recebem a MESMA resposta 401,
    # sem revelar qual condicao falhou. NUNCA logar o CPF.
    if cliente is None or not cliente.ativo:
        _logger.info(
            "Autenticacao negada para CPF nao autorizado",
            extra={"request_id": request_id},
        )
        return _resposta(
            401,
            {"detail": "Credenciais invalidas"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    _logger.info("Token emitido para cliente ativo", extra={"request_id": request_id})
    access_token = token.emitir_access_token(cliente.id, cliente.contato)
    return _resposta(
        200,
        {
            "access_token": access_token,
            "token_type": "bearer",  # nosec B105 - tipo do token, nao senha
            "expires_in": token.EXPIRACAO_MINUTOS * 60,
        },
    )
