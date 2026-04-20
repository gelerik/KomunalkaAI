from core.receipt_parser import extract_receipt_data


def test_extract_receipt_data_happy_path() -> None:
    text = """
    Итого к оплате 5 321,45
    ХВС расход 7,5 м3
    ГВС расход 2,3 м3
    Электроэнергия 145 кВт
    """
    result = extract_receipt_data(text)

    assert result.total_amount == 5321.45
    assert result.water_volume == 9.8
    assert result.electricity_volume == 145.0


def test_extract_receipt_data_handles_missing_values() -> None:
    text = "Нечитаемый OCR текст без чисел"
    result = extract_receipt_data(text)

    assert result.total_amount is None
    assert result.water_volume is None
    assert result.electricity_volume is None
