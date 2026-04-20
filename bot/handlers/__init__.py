from aiogram import Router

from .base_handlers import base_router
from .photo_handlers import photo_router

__all__ = ["get_routers"]


def get_routers() -> list[Router]:
    """
    Возвращает список всех роутеров бота.

    Зачем это нужно?
    - Чтобы в точке входа (main.py) подключать все хэндлеры одной строкой,
      а не импортировать каждый модуль вручную.
    - Когда появятся новые модули, достаточно будет зарегистрировать их здесь.
    """

    return [base_router, photo_router]
