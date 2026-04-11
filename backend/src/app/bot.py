import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

logger = logging.getLogger(__name__)

router = Router()


def _make_app(webapp_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть Sphinx", web_app=WebAppInfo(url=webapp_url))
    ]])


def build_dispatcher(webapp_url: str) -> Dispatcher:
    dp = Dispatcher()
    dp["webapp_url"] = webapp_url
    dp.include_router(router)
    return dp


@router.message(CommandStart())
async def handle_start(message: Message, webapp_url: str) -> None:
    await message.answer(
        "Привет! Sphinx поможет тебе подготовиться к техническому собеседованию.\n\n"
        "Нажми кнопку ниже, чтобы начать:",
        reply_markup=_make_app(webapp_url),
    )
