from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any

import pytest

from src.autenticacao_cpf import db, handler, logging_json

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


@pytest.mark.parametrize(
    "body",
    [
        base64.b64encode(b"\xff\xfe{").decode(),  # decodifica, mas nao e UTF-8
        "%%%nao-e-base64%%%",  # base64 invalido (binascii.Error)
    ],
)
def test_400_base64_invalido(body: str) -> None:
    # Borda de parse inteira dentro do try: entrada malformada e 400, nunca 500.
    resposta = handler.lambda_handler(_evento(body, base64_encoded=True), None)
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
    assert resposta["headers"]["WWW-Authenticate"] == "Bearer"


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


def test_log_json_com_request_id_e_sem_cpf(monkeypatch: pytest.MonkeyPatch) -> None:
    """RNF-029: linha de log e JSON parseavel, carrega request_id e NUNCA o CPF."""
    _mock_cliente(monkeypatch, None)
    buf = io.StringIO()
    captura = logging.StreamHandler(buf)
    captura.setFormatter(logging_json.JsonFormatter())
    handler._logger.addHandler(captura)
    try:
        evento = _evento(json.dumps({"cpf": CPF_VALIDO}))
        evento["requestContext"] = {"requestId": "req-123"}
        handler.lambda_handler(evento, None)
    finally:
        handler._logger.removeHandler(captura)

    saida = buf.getvalue()
    linha = json.loads(saida.strip())
    assert linha["level"] == "INFO"
    assert linha["request_id"] == "req-123"
    assert CPF_VALIDO not in saida
    assert "52998224725" not in saida  # nem o CPF normalizado
