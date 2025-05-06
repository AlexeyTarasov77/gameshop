from decimal import Decimal
from gamesparser.psn import random
import pytest
from unittest.mock import patch
from gateways.currency_converter.schemas import PriceUnitDTO
from products.domain.services import XboxPriceCalculator


def new_test_price(value: Decimal | None = None, currency_code: str = "usd"):
    return PriceUnitDTO.model_validate(
        {"value": value or random.randint(1, 100), "currency_code": currency_code}
    )


class TestXboxPriceCalculator:
    def test_calc_invalid_currency(self):
        with pytest.raises(Exception):
            XboxPriceCalculator(new_test_price(currency_code="uah"))

    def test_calc_for_region(self):
        price = new_test_price()
        calculator = XboxPriceCalculator(price)
        with patch.object(calculator, "_calc_for_us") as calc_us_mock:
            calculator.calc_for_region("us", with_gp=True)
            calc_us_mock.assert_called_once_with(with_gp=True)
        # check raises if with_gp not supplied
        with pytest.raises(Exception):
            calculator.calc_for_region("us")

        with patch.object(calculator, "_calc_for_ar") as calc_ar_mock:
            calculator.calc_for_region("ar", someparam=1)
            calc_ar_mock.assert_called_once_with(someparam=1)
        with patch.object(calculator, "_calc_for_tr") as calc_tr_mock:
            calculator.calc_for_region("tr")
            calc_tr_mock.assert_called_once_with()
        with pytest.raises(ValueError):
            res = calculator.calc_for_region("unknown")
            print("res", res)

    @pytest.mark.parametrize(
        ["input", "expected_percent", "with_gp"],
        [
            (Decimal("2.99") / Decimal("0.73"), 70, False),
            (Decimal("3.00") / Decimal("0.73"), 55, False),
            (Decimal("4.99") / Decimal("0.73"), 55, False),
            (Decimal("5.00") / Decimal("0.73"), 35, False),
            (Decimal("12.99") / Decimal("0.73"), 35, False),
            (Decimal("13.00") / Decimal("0.73"), 33, False),
            (Decimal("19.99") / Decimal("0.73"), 33, False),
            (Decimal("20.00") / Decimal("0.73"), 31, False),
            (Decimal("29.99") / Decimal("0.73"), 31, False),
            (Decimal("30.00") / Decimal("0.73"), 30, False),
            (Decimal("34.99") / Decimal("0.73"), 30, False),
            (Decimal("35.00") / Decimal("0.73"), 28, False),
            (Decimal("39.99") / Decimal("0.73"), 28, False),
            (Decimal("40.00") / Decimal("0.73"), 25, False),
            (Decimal("49.99") / Decimal("0.73"), 25, False),
            (Decimal("50.00") / Decimal("0.73"), 23, False),
            (Decimal("54.99") / Decimal("0.73"), 23, False),
            (Decimal("55.00") / Decimal("0.73"), 20, False),
            (Decimal("70.00") / Decimal("0.73"), 20, False),
            (Decimal("2.00"), 70, True),
            (Decimal("5.00"), 55, True),
            (Decimal("6.99"), 35, True),
        ],
    )
    def test_calc_usa(self, input: Decimal, expected_percent: int, with_gp: bool):
        calculator = XboxPriceCalculator(new_test_price(Decimal(input)))
        res = calculator.calc_for_region("us", with_gp=with_gp)
        input = input * Decimal("0.73")
        if with_gp:
            input += 1
        expected = calculator._add_percent(input, expected_percent)
        assert res.quantize(Decimal(".01")) == expected.quantize(Decimal(".01"))

    @pytest.mark.parametrize(
        ["input", "expected_percent"],
        [
            (0.99, 200),
            (1.0, 150),
            (1.99, 150),
            (2.0, 80),
            (2.99, 80),
            (3.0, 65),
            (4.99, 65),
            (5.0, 55),
            (7.99, 55),
            (8.0, 40),
            (9.99, 40),
            (10.0, 35),
            (12.99, 35),
            (13.0, 32),
            (15.99, 32),
            (16.0, 28),
            (19.99, 28),
            (20.0, 25),
            (24.99, 25),
            (25.0, 24),
            (29.99, 24),
            (30.0, 21),
        ],
    )
    def test_calc_tr(self, input: float, expected_percent: int):
        input_decimal = Decimal(str(input))
        calculator = XboxPriceCalculator(new_test_price(input_decimal))
        res = calculator.calc_for_region("tr")
        expected = calculator._add_percent(input_decimal, expected_percent)
        assert res.quantize(Decimal(".01")) == expected.quantize(Decimal(".01"))

    @pytest.mark.parametrize(
        ["input", "expected_addend"],
        [
            (0.2, Decimal("3.4")),
            (0.21, Decimal("5")),
            (2.0, Decimal("5")),
            (2.01, Decimal("7")),
            (5.0, Decimal("7")),
            (5.01, Decimal("10")),
            (15.0, Decimal("10")),
            (15.01, Decimal("12")),
            (25.0, Decimal("12")),
            (25.01, Decimal("14")),
            (30.0, Decimal("14")),
        ],
    )
    def test_calc_ar(self, input: float, expected_addend: Decimal):
        input_decimal = Decimal(str(input))
        calculator = XboxPriceCalculator(new_test_price(input_decimal))
        res = calculator.calc_for_region("ar")

        if input_decimal > Decimal("0.2"):
            calculated = input_decimal * Decimal("1.7") / Decimal("1.1")
        else:
            calculated = Decimal("0")

        expected = calculated + expected_addend
        assert res.quantize(Decimal(".01")) == expected.quantize(Decimal(".01"))
