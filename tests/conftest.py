"""Env de teste definido ANTES de qualquer import de src (cold start dos modulos)."""

from __future__ import annotations

import os

os.environ.setdefault("ENCRYPTION_KEY", "chave-teste-lambda")
os.environ.setdefault("JWT_SECRET", "segredo-teste-lambda")
os.environ.setdefault("JWT_EXPIRATION_MINUTES", "30")
