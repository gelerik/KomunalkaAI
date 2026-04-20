from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ReceiptData:
    total_amount: float | None
    water_volume: float | None
    electricity_volume: float | None


LATIN_TO_CYRILLIC_MAP = str.maketrans(
    {
        "a": "а",
        "b": "в",
        "c": "с",
        "e": "е",
        "h": "н",
        "k": "к",
        "m": "м",
        "o": "о",
        "p": "р",
        "t": "т",
        "x": "х",
        "y": "у",
    }
)


def _to_float(raw: str) -> float | None:
    normalized = raw.replace(" ", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def extract_receipt_data(text: str) -> ReceiptData:
    """
    Достаёт из OCR-текста ключевые поля для MVP:
    - итоговая сумма;
    - объём воды;
    - объём электричества.
    """
    lines = [_normalize_line(line) for line in text.splitlines() if line.strip()]

    # 1) ИТОГОВАЯ СУММА: ищем по приоритетным якорям и берём денежное значение.
    total_amount = _extract_total_amount(lines)

    # 2) ВОДА: суммируем объёмы из строк с ХВС/ГВС/водоотведением.
    water_volume = _extract_water_volume(lines)

    # 3) ЭЛЕКТРИЧЕСТВО: ищем объём рядом с электро/кВт.
    electricity_volume = _extract_electricity_volume(lines)

    return ReceiptData(
        total_amount=total_amount,
        water_volume=water_volume,
        electricity_volume=electricity_volume,
    )


def _extract_total_amount(lines: list[str]) -> float | None:
    priority_groups = [
        ("к оплате", "коплате"),
        ("всего по видам оказанных услуг", "всего по видам"),
        ("итого к оплате", "итого к оп"),
        ("итого",),
    ]

    for group in priority_groups:
        candidates: list[float] = []
        for line in lines:
            if any(marker in line for marker in group):
                for value in _extract_money_candidates(line):
                    if 50 <= value <= 100000:
                        candidates.append(value)
        if candidates:
            # Для итогов обычно корректнее брать наибольшее значение.
            return max(candidates)

    # Fallback: если якорей нет, берём наибольшее денежное значение в разумном диапазоне.
    all_money: list[float] = []
    for line in lines:
        for value in _extract_money_candidates(line):
            if 50 <= value <= 100000:
                all_money.append(value)
    if all_money:
        return max(all_money)
    return None


def _extract_water_volume(lines: list[str]) -> float | None:
    water_keywords = ("хвс", "гвс", "водоотвед", "водоснаб", "вода")
    total = 0.0
    found = False

    for line in lines:
        if not any(k in line for k in water_keywords):
            continue
        if "1650-1700" in line or "м2" in line:
            continue

        for value in _extract_numeric_candidates(line):
            # Отсекаем явно нерелевантные числа (площади, тарифные диапазоны и т.д.)
            if 0 < value <= 100:
                total += value
                found = True
                break

    # Fallback: если сервисные строки воды не поймались,
    # пытаемся взять расход из раздела с показаниями приборов учёта.
    if not found:
        for line in lines:
            if "расход" not in line:
                continue
            values = [v for v in _extract_numeric_candidates(line) if 0 < v <= 100]
            if values:
                total += sum(values[:2])  # обычно 1-2 строки воды
                found = True
                break

    if not found:
        return None
    return round(total, 3)


def _extract_electricity_volume(lines: list[str]) -> float | None:
    electricity_keywords = ("электро", "квт", "электроэнерг")
    for line in lines:
        if not any(k in line for k in electricity_keywords):
            continue

        for value in _extract_numeric_candidates(line):
            if 0 < value <= 10000:
                return round(value, 3)
    return None


def _extract_money_candidates(line: str) -> list[float]:
    # Денежные значения чаще имеют 2 знака после запятой.
    raws = re.findall(r"\d[\d\s]*[.,]\d{2}", line)
    values: list[float] = []
    for raw in raws:
        value = _to_float(raw)
        if value is not None:
            values.append(value)
    return values


def _extract_numeric_candidates(line: str) -> list[float]:
    raws = re.findall(r"\d[\d\s]*[.,]\d+|\d+", line)
    values: list[float] = []
    for raw in raws:
        value = _to_float(raw)
        if value is not None:
            values.append(value)
    return values


def _normalize_line(line: str) -> str:
    normalized = line.strip().lower().translate(LATIN_TO_CYRILLIC_MAP)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized

