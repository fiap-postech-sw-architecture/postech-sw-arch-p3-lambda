"""Function serverless de autenticacao por CPF (PytStop, fase 3)."""

from __future__ import annotations

import os


def env_obrigatoria(nome: str) -> str:
    """Le uma variavel de ambiente obrigatoria; RuntimeError no cold start se ausente.

    Sem defaults inseguros: segredos ausentes abortam o boot da function em vez
    de emitir tokens assinados com chave vazia/efemera.
    """
    valor = os.environ.get(nome)
    if not valor:
        msg = f"Variavel de ambiente obrigatoria ausente: {nome}"
        raise RuntimeError(msg)
    return valor
