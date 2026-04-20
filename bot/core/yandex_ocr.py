from __future__ import annotations

import base64
import logging
from typing import Any

import aiohttp

from core.config import load_config

logger = logging.getLogger(__name__)

YANDEX_VISION_URL = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"


async def recognize_text(image_bytes: bytes) -> str:
    """
    Отправляет изображение в Yandex Vision OCR и возвращает распознанный текст.

    Алгоритм:
    1) Кодируем байты изображения в Base64 (API принимает content именно в таком виде).
    2) Формируем payload для метода batchAnalyze:
       - model: "ocr"
       - modelVersion: "latest"
       - ocrConfig.languageCodes: ["ru"]
       - features.type: "TEXT_DETECTION"
    3) Делаем POST-запрос с заголовком Authorization: Api-Key <ключ>.
    4) Проходим по JSON-ответу и собираем все words[].text в финальные строки.
    """

    config = load_config()
    if not config.yandex_api_key or not config.yandex_folder_id:
        raise RuntimeError(
            "В .env должны быть заданы YANDEX_API_KEY и YANDEX_FOLDER_ID."
        )

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    # Структура запроса для batchAnalyze:
    # - folderId: папка в Yandex Cloud
    # - analyze_specs: список задач анализа (можно отправлять сразу несколько)
    payload: dict[str, Any] = {
        "folderId": config.yandex_folder_id,
        "analyzeSpecs": [
            {
                "content": encoded_image,
                "features": [
                    {
                        "type": "TEXT_DETECTION",
                        "textDetectionConfig": {
                            "languageCodes": ["ru"],
                        },
                    }
                ],
            }
        ],
    }

    headers = {
        "Authorization": f"Api-Key {config.yandex_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                YANDEX_VISION_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    # Обязательно печатаем "сырое" тело ответа API,
                    # чтобы сразу видеть точную причину ошибки в терминале.
                    error_body = await response.text()
                    print(error_body)
                    raise RuntimeError(
                        f"Yandex Vision вернул статус {response.status}: {error_body}"
                    )

                data = await response.json()
    except aiohttp.ClientError as e:
        logging.error(f"Ошибка OCR: {e}", exc_info=True)
        raise RuntimeError("Не удалось обратиться к Yandex Vision API.") from e
    except Exception as e:
        logging.error(f"Ошибка OCR: {e}", exc_info=True)
        raise RuntimeError("Ошибка во время OCR-анализа.") from e

    try:
        lines: list[str] = []
        results = data.get("results", [])
        for analyze_result in results:
            feature_results = analyze_result.get("results", [])
            for feature_result in feature_results:
                text_detection = feature_result.get("textDetection", {})
                pages = text_detection.get("pages", [])
                for page in pages:
                    blocks = page.get("blocks", [])
                    for block in blocks:
                        block_lines = block.get("lines", [])
                        for line in block_lines:
                            words = line.get("words", [])
                            line_text = " ".join(
                                word.get("text", "").strip()
                                for word in words
                                if word.get("text")
                            ).strip()
                            if line_text:
                                lines.append(line_text)

        if not lines:
            return "Текст на изображении не найден."

        return "\n".join(lines)
    except Exception as e:
        logging.error(f"Ошибка OCR: {e}", exc_info=True)
        raise RuntimeError("Не удалось разобрать ответ OCR.") from e

