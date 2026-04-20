from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


class Config:
    """
    Конфигурация проекта.

    Отдельный класс нужен, чтобы:
    - не читать переменные окружения "изо всех углов" проекта;
    - в одном месте проверять, что обязательные настройки действительно заданы.
    """

    def __init__(self) -> None:
        # Загружаем переменные окружения из файла .env в текущей рабочей директории.
        # Уже существующие переменные окружения НЕ будут перезаписаны.
        load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

        # Токен бота берём строго из переменной окружения BOT_TOKEN.
        # В .env это будет строка вида: BOT_TOKEN=123456:ABC-DEF...
        self.bot_token: str | None = os.getenv("BOT_TOKEN")
        self.yandex_folder_id: str | None = os.getenv("YANDEX_FOLDER_ID")
        self.yandex_api_key: str | None = os.getenv("YANDEX_API_KEY")

        if not self.bot_token:
            # Если токен не найден — сразу останавливаем приложение
            # с понятной для разработчика ошибкой.
            raise RuntimeError(
                "Не найден BOT_TOKEN. Создай файл .env рядом с bot/main.py "
                "и добавь строку BOT_TOKEN=... (пример см. в .env.example)."
            )


def load_config() -> Config:
    """
    Удобная функция-обёртка для создания объекта Config.

    Почему так?
    - Когда проект вырастет, сюда можно будет добавить кеширование
      или более сложную логику инициализации.
    """

    return Config()
