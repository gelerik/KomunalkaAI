import io
import logging

from aiogram import F, Router
from aiogram.types import Message

from core.config import load_config
from core.image_preprocess import build_preprocessed_rotations
from core.llm_parser import extract_data_with_yandexgpt
from core.tariffs import MOSCOW_TARIFFS
from core.yandex_ocr import recognize_text

# Отдельный роутер для работы с фотографиями и "прочими" сообщениями.
photo_router = Router()
logger = logging.getLogger(__name__)


def _fmt_number(value: float | None, unit: str = "") -> str:
    if value is None:
        return "не найдено"
    if unit:
        return f"{value:.2f} {unit}"
    return f"{value:.2f}"


def _fmt_receipt_block(value: float | None, unit: str) -> str:
    if value is None:
        return "отсутствует в квитанции"
    return _fmt_number(value, unit)


def _fmt_delta(receipt_value: float | None, calculated_value: float | None) -> str:
    if receipt_value is None or calculated_value is None:
        return "недостаточно данных для сверки"
    delta = round(receipt_value - calculated_value, 2)
    if delta > 0:
        return f"возможная переплата: {delta:.2f} руб."
    if delta < 0:
        return f"возможная недоплата: {abs(delta):.2f} руб."
    return "расхождение не обнаружено"


async def _process_receipt_bytes(message: Message, image_bytes: bytes) -> None:
    """
    Общий пайплайн обработки изображения квитанции.
    Используется и для фото, и для файла-документа.
    """
    # Готовим 4 варианта изображения (0/90/180/270) после кропа и повышения контраста.
    # Затем прогоняем OCR для каждого и берём вариант с самым "информативным" текстом.
    best_text = ""
    for _, prepared_bytes in build_preprocessed_rotations(image_bytes):
        candidate_text = await recognize_text(image_bytes=prepared_bytes)
        score = len("".join(candidate_text.split()))
        if score > len("".join(best_text.split())):
            best_text = candidate_text

    config = load_config()
    llm_data = await extract_data_with_yandexgpt(
        raw_text=best_text,
        folder_id=config.yandex_folder_id or "",
        api_key=config.yandex_api_key or "",
    )

    cold_m3 = llm_data.get("cold_water_m3")
    hot_m3 = llm_data.get("hot_water_m3")
    elect_kwh = llm_data.get("electricity_kwh")
    cold_water_rub = llm_data.get("cold_water_rub")
    hot_water_rub = llm_data.get("hot_water_rub")
    electricity_rub = llm_data.get("electricity_rub")
    maintenance_rub = llm_data.get("maintenance_rub")
    cap_repair_rub = llm_data.get("cap_repair_rub")
    area_m2 = llm_data.get("area_m2")
    total_sum = llm_data.get("total_sum")

    # Самостоятельный расчёт бота по условным тарифам.
    calc_cold = (
        round(cold_m3 * MOSCOW_TARIFFS["cold_water_m3"], 2) if cold_m3 is not None else None
    )
    calc_hot = (
        round(hot_m3 * MOSCOW_TARIFFS["hot_water_m3"], 2) if hot_m3 is not None else None
    )
    calc_electricity = (
        round(elect_kwh * MOSCOW_TARIFFS["electricity_kwh"], 2)
        if elect_kwh is not None
        else None
    )
    calc_maintenance = (
        round(area_m2 * MOSCOW_TARIFFS["maintenance_m2"], 2) if area_m2 is not None else None
    )
    calc_cap_repair = (
        round(area_m2 * MOSCOW_TARIFFS["cap_repair_m2"], 2) if area_m2 is not None else None
    )

    computed_items = [
        calc_cold or 0.0,
        calc_hot or 0.0,
        calc_electricity or 0.0,
        calc_maintenance or 0.0,
        calc_cap_repair or 0.0,
    ]
    computed_total = round(sum(computed_items), 2) if any(computed_items) else None

    # Сверка с квитанцией по блокам (где есть данные).
    utility_receipt_sum_items = [
        cold_water_rub or 0.0,
        hot_water_rub or 0.0,
        electricity_rub or 0.0,
        maintenance_rub or 0.0,
        cap_repair_rub or 0.0,
    ]
    utility_receipt_sum = (
        round(sum(utility_receipt_sum_items), 2) if any(utility_receipt_sum_items) else None
    )

    await message.answer(
        "🧾 Данные из квитанции:\n"
        f"- Итого к оплате: {_fmt_receipt_block(total_sum, 'руб.')}\n"
        f"- ХВС (объём): {_fmt_receipt_block(cold_m3, 'м3')}\n"
        f"- ХВС (начисление): {_fmt_receipt_block(cold_water_rub, 'руб.')}\n"
        f"- ГВС (объём): {_fmt_receipt_block(hot_m3, 'м3')}\n"
        f"- ГВС (начисление): {_fmt_receipt_block(hot_water_rub, 'руб.')}\n"
        f"- Электричество (объём): {_fmt_receipt_block(elect_kwh, 'кВт.ч')}\n"
        f"- Электричество (начисление): {_fmt_receipt_block(electricity_rub, 'руб.')}\n"
        f"- Содержание/ремонт: {_fmt_receipt_block(maintenance_rub, 'руб.')}\n"
        f"- Капремонт: {_fmt_receipt_block(cap_repair_rub, 'руб.')}\n"
        f"- Площадь квартиры: {_fmt_receipt_block(area_m2, 'м2')}\n\n"
        "🤖 Самостоятельный расчёт по условным тарифам:\n"
        f"- ХВС: {_fmt_number(calc_cold, 'руб.')}\n"
        f"- ГВС: {_fmt_number(calc_hot, 'руб.')}\n"
        f"- Электричество: {_fmt_number(calc_electricity, 'руб.')}\n"
        f"- Содержание/ремонт (по площади): {_fmt_number(calc_maintenance, 'руб.')}\n"
        f"- Капремонт (по площади): {_fmt_number(calc_cap_repair, 'руб.')}\n"
        f"- Итого расчёт бота: {_fmt_number(computed_total, 'руб.')}\n\n"
        "📊 Сверка и потенциальные расхождения:\n"
        f"- По ХВС: {_fmt_delta(cold_water_rub, calc_cold)}\n"
        f"- По ГВС: {_fmt_delta(hot_water_rub, calc_hot)}\n"
        f"- По электричеству: {_fmt_delta(electricity_rub, calc_electricity)}\n"
        f"- По общему итогу (квитанция vs расчёт бота): {_fmt_delta(total_sum, computed_total)}\n"
        f"- По сумме найденных блоков квитанции vs расчёт бота: {_fmt_delta(utility_receipt_sum, computed_total)}"
    )


@photo_router.message(F.photo)
async def handle_receipt_photo(message: Message) -> None:
    """
    Хэндлер, который срабатывает, когда пользователь отправляет фотографию.

    Что делаем:
    1) Берём фото наивысшего качества: message.photo[-1].
    2) Скачиваем его в память (io.BytesIO), без сохранения на диск.
    3) Отправляем байты в OCR-функцию и возвращаем пользователю результат.
    """
    await message.answer("Квитанция получена! Начинаю анализ...")

    try:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)

        image_buffer = io.BytesIO()
        await message.bot.download(file, destination=image_buffer)
        image_bytes = image_buffer.getvalue()

        await _process_receipt_bytes(message, image_bytes)
    except Exception:
        logger.exception("Ошибка при обработке фото пользователя")
        await message.answer(
            "Извини, не получилось распознать текст на фото. "
            "Попробуй отправить более чёткое изображение чуть позже."
        )


@photo_router.message(F.document)
async def handle_receipt_document(message: Message) -> None:
    """
    Хэндлер для квитанции, отправленной как файл (document).
    Такой вариант обычно лучше по качеству, потому что Telegram не сжимает картинку.
    """
    await message.answer("Файл квитанции получен! Начинаю анализ...")

    try:
        if not message.document:
            await message.answer("Не удалось получить файл. Попробуй отправить еще раз.")
            return

        # Принимаем только изображения (image/jpeg, image/png и т.п.).
        if not (message.document.mime_type or "").startswith("image/"):
            await message.answer(
                "Пожалуйста, отправь квитанцию как изображение (JPG/PNG) в формате файла."
            )
            return

        file = await message.bot.get_file(message.document.file_id)
        image_buffer = io.BytesIO()
        await message.bot.download(file, destination=image_buffer)
        image_bytes = image_buffer.getvalue()

        await _process_receipt_bytes(message, image_bytes)
    except Exception:
        logger.exception("Ошибка при обработке файла пользователя")
        await message.answer(
            "Извини, не получилось распознать текст из файла. "
            "Попробуй отправить более чёткий JPG/PNG."
        )


@photo_router.message(~F.photo & ~F.document & ~F.text.startswith("/"))
async def handle_non_photo(message: Message) -> None:
    """
    Хэндлер для всех других типов сообщений:
    - обычный текст (не команда),
    - стикеры,
    - голосовые, видео и т.д.

    Фильтр ~F.photo говорит: "сообщение НЕ должно содержать фото".
    Фильтр ~F.text.startswith('/') отфильтровывает команды (/start, /help, ...),
    чтобы ими занимался модуль base_handlers.
    """

    await message.answer(
        "Пожалуйста, отправь мне фотографию квитанции ЖКХ 📷 "
        "или файл-изображение (JPG/PNG) 📎."
    )

