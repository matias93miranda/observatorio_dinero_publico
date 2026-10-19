from decimal import Decimal

import pytest

from observatorio.money import AmountError, centavos_to_millones, millones_to_centavos, parse_decimal


def test_coma_decimal_exacta():
    assert millones_to_centavos("112314,626039") == 11231462603900
    assert millones_to_centavos("6150,27186675") == 615027186675
    assert millones_to_centavos("450") == 45000000000


def test_ida_y_vuelta_sin_perdida():
    assert centavos_to_millones(millones_to_centavos("117476799,88051809")) == Decimal("117476799.88051809")


@pytest.mark.parametrize("bad", ["", "  ", "abc", "1.234,5"])
def test_vacio_o_invalido_no_es_cero(bad):
    with pytest.raises(AmountError):
        millones_to_centavos(bad)


def test_precision_sub_centavo_falla():
    with pytest.raises(AmountError):
        millones_to_centavos("1,000000001")


def test_negativos():
    assert parse_decimal("-3,5") == Decimal("-3.5")
