from __future__ import annotations

from dataclasses import dataclass

from core.receipt_parser import ReceiptData
from core.tariffs import MOSCOW_TARIFFS


@dataclass
class AnalysisResult:
    expected_amount: float | None
    overpayment: float | None
    message: str


def analyze_receipt(data: ReceiptData) -> AnalysisResult:
    """
    Сравнивает сумму из квитанции с MVP-расчётом по захардкоженным тарифам.
    Формула MVP: expected = water_volume * tariff_water + electricity_volume * tariff_electricity
    """
    if data.total_amount is None:
        return AnalysisResult(
            expected_amount=None,
            overpayment=None,
            message="Не удалось определить итоговую сумму в квитанции.",
        )

    if data.water_volume is None and data.electricity_volume is None:
        return AnalysisResult(
            expected_amount=None,
            overpayment=None,
            message="Не удалось определить объёмы воды и электричества.",
        )

    water_cost = (data.water_volume or 0.0) * MOSCOW_TARIFFS["water"]
    electricity_cost = (data.electricity_volume or 0.0) * MOSCOW_TARIFFS["electricity"]
    expected = round(water_cost + electricity_cost, 2)

    if data.water_volume is None or data.electricity_volume is None:
        return AnalysisResult(
            expected_amount=expected,
            overpayment=None,
            message=(
                "Часть показаний не удалось надёжно извлечь, "
                "поэтому расчёт ориентировочный и требует ручной проверки."
            ),
        )

    delta = round(data.total_amount - expected, 2)
    if delta > 0:
        message = (
            f"По нашим данным, возможная переплата составляет примерно {delta:.2f} руб."
        )
    elif delta < 0:
        message = (
            f"По нашим данным, начислено меньше ожидаемого примерно на {abs(delta):.2f} руб."
        )
    else:
        message = "По нашим данным, явных расхождений по сумме не обнаружено."

    return AnalysisResult(
        expected_amount=expected,
        overpayment=delta,
        message=message,
    )

