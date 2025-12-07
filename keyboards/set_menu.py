from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon import LEXICON_RU


def main_menu_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    buttons = [
        InlineKeyboardButton(
            text=LEXICON_RU["main_menu_button_pickteam"],
            callback_data="pickteam"
        ),
        InlineKeyboardButton(
            text=LEXICON_RU["main_menu_button_myteam"],
            callback_data="myteam"
        ),
        InlineKeyboardButton(
            text=LEXICON_RU["main_menu_button_schedule"],
            callback_data="schedule"
        ),
        InlineKeyboardButton(
            text=LEXICON_RU["main_menu_button_leaderboard"],
            callback_data="leaderboard"
        ),
        InlineKeyboardButton(
            text=LEXICON_RU["main_menu_button_resetteam"],
            callback_data="resetteam"
        )
    ]
    kb_builder.row(buttons[0], buttons[1], width=2)
    kb_builder.row(buttons[2], width=1)
    kb_builder.row(buttons[3], buttons[4], width=2)
    return kb_builder.as_markup()
