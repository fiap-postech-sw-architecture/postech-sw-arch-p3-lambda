"""Validacao de CPF por modulo 11, executada antes de qualquer acesso ao banco.

Um CPF tem 9 digitos de base e 2 digitos verificadores (DV). Cada DV e o modulo
11 da soma ponderada dos digitos anteriores: pesos decrescentes de ``n + 1`` ate
2 (``n`` = quantidade de digitos considerados). Com ``r`` o resto da divisao da
soma por 11, o DV e 0 quando ``r < 2`` e ``11 - r`` nos demais casos.

O handler responde 400 ao que nao passa aqui e poupa ao RDS uma consulta (e uma
conexao) para documentos que nao existem por construcao. A entrada e o documento
ja normalizado (``hashing.normalizar_documento``): so digitos ASCII.
"""

from __future__ import annotations

TAMANHO = 11
_TAMANHO_BASE = 9


def _digito_verificador(digitos: str) -> int:
    """DV (modulo 11) dos ``digitos`` informados, ja sem mascara."""
    pesos = range(len(digitos) + 1, 1, -1)
    soma = sum(int(d) * peso for d, peso in zip(digitos, pesos, strict=True))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(cpf: str) -> bool:
    """True se ``cpf`` tem 11 digitos ASCII, nao e sequencia repetida e os DVs batem.

    Sequencias como ``111.111.111-11`` passam no calculo, mas nao sao CPFs
    emitidos pela Receita; sao rejeitadas explicitamente. Digitos de outros
    alfabetos (ex.: arabe-indicos) tambem sao rejeitados: gerariam um
    ``documento_hash`` diferente do cadastrado e so custariam uma ida ao banco.
    """
    if len(cpf) != TAMANHO or not (cpf.isascii() and cpf.isdigit()):
        return False
    if cpf == cpf[0] * TAMANHO:
        return False
    base = cpf[:_TAMANHO_BASE]
    dv1 = _digito_verificador(base)
    dv2 = _digito_verificador(f"{base}{dv1}")
    return cpf[_TAMANHO_BASE:] == f"{dv1}{dv2}"
