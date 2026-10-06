from __future__ import annotations

import random

import pytest
from brutils.cpf import is_valid as brutils_is_valid

from src.autenticacao_cpf.cpf import _digito_verificador, cpf_valido

# CPFs de exemplo amplamente usados em documentacao (nao pertencem a pessoas reais).
VALIDOS = [
    "52998224725",
    "11144477735",
    "39053344705",
    "12345678909",
    "00000000191",  # zeros a esquerda: o DV nao pode depender de int(cpf)
]

# Mesmo CPF valido (529.982.247-25) escrito com digitos de outros alfabetos,
# montados por codepoint para a fonte nao depender de caracteres ambiguos.
ARABE_INDICO = "".join(chr(0x0660 + int(d)) for d in "52998224725")
LARGURA_TOTAL = "".join(chr(0xFF10 + int(d)) for d in "52998224725")


@pytest.mark.parametrize("cpf", VALIDOS)
def test_aceita_cpf_com_digitos_verificadores_corretos(cpf: str) -> None:
    assert cpf_valido(cpf)


def test_digito_verificador_exemplo_didatico() -> None:
    """529.982.247-25: DV1 sobre os 9 digitos, DV2 sobre os 9 + DV1."""
    assert _digito_verificador("529982247") == 2
    assert _digito_verificador("5299822472") == 5


@pytest.mark.parametrize(
    "cpf",
    [
        "52998224735",  # primeiro DV errado
        "52998224726",  # segundo DV errado
        "52998224700",  # ambos errados
        "12345678900",
    ],
)
def test_rejeita_digitos_verificadores_errados(cpf: str) -> None:
    assert not cpf_valido(cpf)


@pytest.mark.parametrize("digito", "0123456789")
def test_rejeita_sequencia_de_digitos_repetidos(digito: str) -> None:
    # 000.000.000-00 passa no calculo do modulo 11, mas nao e um CPF emitido.
    assert not cpf_valido(digito * 11)


@pytest.mark.parametrize(
    "cpf",
    [
        "",
        "5299822472",  # 10 digitos
        "529982247250",  # 12 digitos
        "529.982.247-25",  # mascara: a funcao recebe o documento ja normalizado
        " 52998224725",
        "5299822472a",
        "5299822472\n",
    ],
)
def test_rejeita_formato_diferente_de_11_digitos(cpf: str) -> None:
    assert not cpf_valido(cpf)


@pytest.mark.parametrize(
    "cpf",
    [
        ARABE_INDICO,  # brutils aceita; geraria um hash diferente do cadastrado
        LARGURA_TOTAL,
        "5299822472\u00b2",  # sobrescrito: isdigit() e True, int() levanta ValueError
    ],
)
def test_rejeita_digitos_nao_ascii(cpf: str) -> None:
    assert not cpf_valido(cpf)


def test_paridade_com_brutils_em_amostra_deterministica() -> None:
    """O validador proprio decide igual a brutils (que o app usa) em ASCII.

    Amostra com semente fixa: 100 mil strings de 11 digitos (cerca de 1% valida)
    mais todas as variacoes de um digito de 100 CPFs validos, que cobrem o erro
    isolado em cada posicao -- inclusive nos DVs.
    """
    rng = random.Random(20260906)
    amostra = [f"{rng.randrange(10**11):011d}" for _ in range(100_000)]
    validos = [c for c in amostra if brutils_is_valid(c)]
    assert len(validos) > 500  # a amostra exercita o ramo "valido"

    variacoes = [
        v[:i] + d + v[i + 1 :]
        for v in validos[:100]
        for i in range(11)
        for d in "0123456789"
        if d != v[i]
    ]
    repetidos = [str(d) * 11 for d in range(10)]

    divergentes = [
        c
        for c in (*amostra, *variacoes, *repetidos, *VALIDOS)
        if cpf_valido(c) != brutils_is_valid(c)
    ]
    assert divergentes == []
