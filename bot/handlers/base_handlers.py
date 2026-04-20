from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

# Создаём отдельный роутер для "базовых" команд (/start, /help).
# Такой подход помогает держать код организованным по смысловым модулям.
base_router = Router()


@base_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Хэндлер для команды /start.

    Как это работает:
    - Декоратор @base_router.message(CommandStart()) говорит aiogram:
      "вызови эту функцию, когда придёт апдейт с командой /start".
    - Объект Message содержит всю информацию о сообщении и отправителе.
    """

    await message.answer(
        "Привет! 👋\n"
        "Я КоммуналкаAI.\n\n"
        "Пришли мне чёткое фото своей квитанции ЖКХ, и я проверю, "
        "нет ли в ней переплат и ошибок."
    )


@base_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Хэндлер для команды /help.

    Здесь мы просто повторяем инструкцию для пользователя.
    """

    await message.answer(
        "Чтобы я мог помочь, пожалуйста:\n"
        "1) Сделай фото квитанции ЖКХ так, чтобы текст было хорошо видно.\n"
        "2) Отправь это фото сюда.\n\n"
        "Я проанализирую данные и позже подскажу, нет ли ошибок или переплат. 📄"
    )
