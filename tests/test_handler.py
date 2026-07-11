from __future__ import annotations

import base64
import json
from typing import Any

import pytest

from src.autenticacao_cpf import db, handler

CPF_VALIDO = "529.982.247-25"


def _evento(body: str | None, *, base64_encoded: bool = False) -> dict[str, Any]:
    return {"body": body, "isBase64Encoded": base64_encoded}


def _corpo(resposta: dict[str, Any]) -> dict[str, Any]:
    corpo: dict[str, Any] = json.loads(resposta["body"])
    return corpo


def _mock_cliente(
    monkeypatch: pytest.MonkeyPatch, cliente: db.Cliente | None
) -> list[str]:
    hashes: list[str] = []

    def fake(documento_hash: str) -> db.Cliente | None:
        hashes.append(documento_hash)
        return cliente

    monkeypatch.setattr(db, "buscar_cliente_por_hash", fake)
    return hashes


def test_200_cliente_ativo(monkeypatch: pytest.MonkeyPatch) -> None:
    hashes = _mock_cliente(
        monkeypatch, db.Cliente(id="abc-1", contato="cli@ex.com", ativo=True)
    )
    resposta = handler.lambda_handler(_evento(json.dumps({"cpf": CPF_VALIDO})), None)
    assert resposta["statusCode"] == 200
    corpo = _corpo(resposta)
    assert corpo["token_type"] == "bearer"
    assert corpo["expires_in"] == 30 * 60
    assert corpo["access_token"]
    # Busca feita pelo hash do CPF normalizado (64 hex chars).
    assert len(hashes) == 1
    assert len(hashes[0]) == 64


def test_400_cpf_malformado(monkeypatch: pytest.MonkeyPatch) -> None:
    hashes = _mock_cliente(monkeypatch, None)
    resposta = handler.lambda_handler(
        _evento(json.dumps({"cpf": "111.111.111-11"})), None
    )
    assert resposta["statusCode"] == 400
    assert _corpo(resposta)["detail"] == "CPF invalido"
    assert hashes == []  # nem chega ao banco


@pytest.mark.parametrize(
    "body",
    [None, "", "nao-e-json", json.dumps({"sem_cpf": 1}), json.dumps({"cpf": 123}), "["],
)
def test_400_corpo_invalido(body: str | None) -> None:
    resposta = handler.lambda_handler(_evento(body), None)
    assert resposta["statusCode"] == 400


def test_body_base64(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_cliente(monkeypatch, db.Cliente(id="abc-1", contato="c@e.com", ativo=True))
    body = base64.b64encode(json.dumps({"cpf": CPF_VALIDO}).encode()).decode()
    resposta = handler.lambda_handler(_evento(body, base64_encoded=True), None)
    assert resposta["statusCode"] == 200


def test_401_cliente_inexistente(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_cliente(monkeypatch, None)
    resposta = handler.lambda_handler(_evento(json.dumps({"cpf": CPF_VALIDO})), None)
    assert resposta["statusCode"] == 401
    assert _corpo(resposta)["detail"] == "Credenciais invalidas"


def test_401_cliente_inativo_mesma_resposta_anti_enumeracao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_cliente(monkeypatch, db.Cliente(id="abc-1", contato="c@e.com", ativo=False))
    inativo = handler.lambda_handler(_evento(json.dumps({"cpf": CPF_VALIDO})), None)

    _mock_cliente(monkeypatch, None)
    inexistente = handler.lambda_handler(_evento(json.dumps({"cpf": CPF_VALIDO})), None)

    # Mesma resposta byte a byte: nao vaza se o cliente existe.
    assert inativo == inexistente
    assert inativo["statusCode"] == 401
