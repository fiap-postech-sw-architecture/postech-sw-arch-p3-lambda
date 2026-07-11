from __future__ import annotations

import hashlib
import hmac
import importlib

import pytest

from src.autenticacao_cpf import hashing

CPF_VALIDO = "52998224725"


def test_normalizar_remove_mascara() -> None:
    assert hashing.normalizar_documento("529.982.247-25") == CPF_VALIDO


def test_normalizar_descarta_tudo_que_nao_e_digito() -> None:
    assert hashing.normalizar_documento(" 529a982b247/25 ") == CPF_VALIDO
    assert hashing.normalizar_documento("abc") == ""


def test_paridade_com_encryption_service_do_app() -> None:
    """CRITICO: replica a formula exata do app (encryption.py::hash_deterministic).

    chave HMAC = sha256(ENCRYPTION_KEY.encode()).digest(); msg = documento
    normalizado. Calculado manualmente aqui com stdlib, independente de
    hashing.py -- se a formula divergir, a busca no banco do app quebra.
    """
    chave = hashlib.sha256(b"chave-teste-lambda").digest()
    esperado = hmac.new(chave, CPF_VALIDO.encode(), hashlib.sha256).hexdigest()
    assert hashing.hash_documento(CPF_VALIDO) == esperado
    # Vetor fixo (pre-calculado): protege contra mudanca simultanea dos dois lados.
    assert (
        esperado == "a6c97bf60b03a9bf13b75bbd37de221db4a2cac0daf2281e9b4387791c4a08be"
    )


def test_cold_start_sem_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENCRYPTION_KEY")
    with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
        importlib.reload(hashing)
    monkeypatch.undo()
    importlib.reload(hashing)
