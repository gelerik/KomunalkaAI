import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.config import load_config
from handlers import get_routers


async def main() -> None:
    """
    Точка входа в приложение.

    Здесь мы:
    1) настраиваем логирование;
    2) загружаем конфигурацию (в т.ч. BOT_TOKEN из .env);
    3) создаём экземпляры Bot и Dispatcher;
    4) подключаем роутеры с хэндлерами;
    5) запускаем "длинный опрос" (long polling) Telegram API.
    """

    # Базовая настройка логирования.
    # level=logging.INFO — значит, что мы будем видеть в консоли
    # информационные сообщения, предупреждения и ошибки.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)
    logger.info("Запуск бота КоммуналкаAI...")

    # Загружаем конфигурацию проекта и берём токен бота из .env.
    config = load_config()

    # Создаём объект бота.
    # В aiogram 3.x "настройки по умолчанию" (включая parse_mode) задаются через DefaultBotProperties.
    # Так мы говорим: "все ответы бота по умолчанию будут интерпретировать разметку как HTML".
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Dispatcher — центральный объект, который получает апдейты от Telegram
    # и передаёт их нужным хэндлерам (в роутерах).
    dp = Dispatcher()

    # Подключаем все роутеры, которые мы описали в пакете handlers.
    # Каждый роутер отвечает за свою "зону ответственности" (команды, фото и т.п.).
    for router in get_routers():
        dp.include_router(router)

    # Стартуем "длинный опрос" (long polling).
    # Бот будет постоянно спрашивать у Telegram: "нет ли для меня новых апдейтов?".
    await dp.start_polling(bot)


if __name__ == "__main__":
    # asyncio.run запускает нашу асинхронную функцию main().
    # Это стандартный способ старта асинхронного приложения в Python 3.10+.
    asyncio.run(main())

