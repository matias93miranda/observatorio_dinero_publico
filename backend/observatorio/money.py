"""Conversión exacta de importes. Nada pasa por float."""
from decimal import Decimal, InvalidOperation

CENTAVOS_POR_MILLON = Decimal(100_000_000)


class AmountError(ValueError):
    pass


def parse_decimal(text: str) -> Decimal:
    """Parsea un número del CSV de Presupuesto Abierto ('112314,626039' o '450').

    Coma = separador decimal; no hay separador de miles en estos archivos.
    Celda vacía => AmountError (el llamador decide; nunca se convierte en 0).
    """
    t = (text or "").strip()
    if not t:
        raise AmountError("celda vacía")
    if "." in t and "," in t:
        raise AmountError(f"formato ambiguo: {text!r}")
    try:
        return Decimal(t.replace(",", "."))
    except InvalidOperation as e:
        raise AmountError(f"no numérico: {text!r}") from e


def millones_to_centavos(text: str) -> int:
    """Millones de pesos (texto) -> centavos enteros; falla si se perdería precisión."""
    c = parse_decimal(text) * CENTAVOS_POR_MILLON
    if c != c.to_integral_value():
        raise AmountError(f"más precisión que centavos: {text!r}")
    return int(c)


def centavos_to_millones(c: int) -> Decimal:
    return Decimal(c) / CENTAVOS_POR_MILLON
