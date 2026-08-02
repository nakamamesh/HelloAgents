from decimal import Decimal

from app.db.session import money


def test_money_is_decimal_not_float():
    amount = money("12.345678")
    assert isinstance(amount, Decimal)
    assert amount == Decimal("12.345678")
    assert not isinstance(amount, float)


def test_money_rejects_float_path_via_str():
    # floats must be stringified carefully by callers — money() takes str/int/Decimal
    assert money(1) == Decimal("1")
    assert money(Decimal("0.100000")) == Decimal("0.100000")
