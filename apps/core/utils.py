from decimal import Decimal, ROUND_HALF_UP

HUNDRED = Decimal("100")
UGX_QUANTIZER = Decimal("1")


def quantize_ugx(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(value).quantize(UGX_QUANTIZER, rounding=ROUND_HALF_UP)
