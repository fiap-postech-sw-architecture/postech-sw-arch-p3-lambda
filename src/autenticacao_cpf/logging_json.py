"""Logging estruturado JSON no stdout (RNF-029, RFC-003 secao 7).

Nivel INFO explicito no logger: o runtime da Lambda configura o root em WARNING,
descartando INFO -- por isso cada modulo configura o proprio logger aqui.
NUNCA logar CPF nem corpo da requisicao.
"""

from __future__ import annotations

import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    """Uma linha JSON por registro; `request_id` entra quando presente."""

    def format(self, record: logging.LogRecord) -> str:
        linha: dict[str, str] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            linha["request_id"] = str(request_id)
        return json.dumps(linha)


def configurar_logger(nome: str) -> logging.Logger:
    """Logger INFO com formatter JSON no stdout, sem propagar ao root da Lambda."""
    logger = logging.getLogger(nome)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
