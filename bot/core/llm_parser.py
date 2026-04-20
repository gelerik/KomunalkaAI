from __future__ import annotations

import json
import logging
import re
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


def _empty_result() -> dict[str, float | None]:
    return {
        "total_sum": None,
        "cold_water_m3": None,
        "hot_water_m3": None,
        "electricity_kwh": None,
        "cold_water_rub": None,
        "hot_water_rub": None,
        "electricity_rub": None,
        "maintenance_rub": None,
        "cap_repair_rub": None,
        "area_m2": None,
    }


def _clean_llm_json(text: str) -> str:
    """
    Убирает markdown-обёртки вида ```json ... ``` и возвращает "чистый" JSON-текст.
    """
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


async def extract_data_with_yandexgpt(
    raw_text: str,
    folder_id: str,
    api_key: str,
) -> dict[str, float | None]:
    """
    Отправляет сырой OCR-текст в YandexGPT и просит вернуть строго JSON
    со структурированными полями по квитанции.
    """
    if not raw_text.strip() or not folder_id or not api_key:
        return _empty_result()

    payload: dict[str, Any] = {
        "modelUri": f"gpt://{folder_id}/yandexgpt-lite/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.0,
            "maxTokens": 300,
        },
        "messages": [
            {
                "role": "system",
                "text": (
                    "Ты — строгий парсер данных из квитанций ЖКХ. "
                    "Твоя задача: найти в кривом OCR тексте квитанции объёмы потребления, "
                    "начисления по основным блокам и итоговую сумму. "
                    "Верни ответ СТРОГО в формате JSON без markdown разметки и лишних слов. "
                    "Структура JSON: "
                    "{\"total_sum\": float или null, "
                    "\"cold_water_m3\": float или null, "
                    "\"hot_water_m3\": float или null, "
                    "\"electricity_kwh\": float или null, "
                    "\"cold_water_rub\": float или null, "
                    "\"hot_water_rub\": float или null, "
                    "\"electricity_rub\": float или null, "
                    "\"maintenance_rub\": float или null, "
                    "\"cap_repair_rub\": float или null, "
                    "\"area_m2\": float или null}. "
                    "Важно: не путай объем и начисление. "
                    "Объем воды указывай только в м3, тариф и начисление не записывай в *_m3. "
                    "В *_rub указывай начисления в рублях по соответствующему блоку."
                ),
            },
            {
                "role": "user",
                "text": raw_text,
            },
        ],
    }

    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                YANDEX_GPT_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=45),
            ) as response:
                if response.status != 200:
                    body = await response.text()
                    logger.error("YandexGPT status %s: %s", response.status, body)
                    return _empty_result()
                data = await response.json()
    except (aiohttp.ClientError, TimeoutError):
        logger.exception("Ошибка запроса к YandexGPT")
        return _empty_result()
    except Exception:
        logger.exception("Неожиданная ошибка при обращении к YandexGPT")
        return _empty_result()

    try:
        llm_text = (
            data.get("result", {})
            .get("alternatives", [{}])[0]
            .get("message", {})
            .get("text", "")
        )
        cleaned = _clean_llm_json(llm_text)
        parsed = json.loads(cleaned)
    except Exception:
        logger.exception("Не удалось распарсить ответ YandexGPT в JSON")
        return _empty_result()

    result = _empty_result()
    for key in result.keys():
        value = parsed.get(key)
        if isinstance(value, (int, float)):
            result[key] = float(value)
        else:
            result[key] = None

    # Пост-валидация: если LLM случайно положила рубли в поле объема воды,
    # считаем это начислением и переносим в *_rub.
    if result["cold_water_m3"] is not None and result["cold_water_m3"] > 20:
        if result["cold_water_rub"] is None:
            result["cold_water_rub"] = result["cold_water_m3"]
        result["cold_water_m3"] = None

    if result["hot_water_m3"] is not None and result["hot_water_m3"] > 20:
        if result["hot_water_rub"] is None:
            result["hot_water_rub"] = result["hot_water_m3"]
        result["hot_water_m3"] = None

    return result

