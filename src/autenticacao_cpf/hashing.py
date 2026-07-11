"""Normalizacao de documento e hash deterministico, em paridade com o app.

Replica EXATAMENTE o app principal (postech-sw-arch-p3):
- normalizacao: descarta tudo que nao e digito
  (``src/cliente_veiculo/dominio/documento.py``);
- hash: HMAC-SHA256 com chave ``sha256(ENCRYPTION_KEY.encode()).digest()``
  (``src/compartilhado/infraestrutura/encryption.py::hash_deterministic``).

Qualquer divergencia aqui quebra a busca por ``documento_hash`` no banco.
"""

from __future__ import annotations

import hashlib
import hmac
import re

from src.autenticacao_cpf import env_obrigatoria

_NAO_DIGITO = re.compile(r"\D")

# Derivada no cold start: ENCRYPTION_KEY ausente aborta o boot (sem fallback).
_HMAC_KEY = hashlib.sha256(env_obrigatoria("ENCRYPTION_KEY").encode()).digest()


def normalizar_documento(documento: str) -> str:
    """Remove mascara: mantem apenas digitos (mesma regra do VO CPF do app)."""
    return _NAO_DIGITO.sub("", documento)


def hash_documento(documento_normalizado: str) -> str:
    """HMAC-SHA256 deterministico do documento normalizado (hex, 64 chars)."""
    return hmac.new(
        _HMAC_KEY, documento_normalizado.encode(), hashlib.sha256
    ).hexdigest()
