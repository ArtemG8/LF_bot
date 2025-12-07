from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon import LEXICON_RU
from config import Config
from typing import List


def pickteam_positions_keyboard(selected_count: int) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for position_key, position_text in Config.POSITIONS.items():
        kb_builder.button(
            text=position_text,
            callback_data=f"select_position_{position_key}"
        )
    kb_builder.adjust(1)

    confirm_button = InlineKeyboardButton(
        text=LEXICON_RU["pickteam_confirm_button"],
        callback_data="confirm_team"
    )
    remove_button = InlineKeyboardButton(
        text=LEXICON_RU["pickteam_remove_button"],
        callback_data="remove_player"
    )
    kb_builder.row(confirm_button, remove_button, width=2)

    return kb_builder.as_markup()


def admin_matches_to_score_keyboard(matches: List[dict]) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for match in matches:
        date_str = match['match_datetime'].strftime("%d.%m.%Y %H:%M")
        kb_builder.button(
            text=f"{date_str} - {match['opponent']}",
            callback_data=f"admin_score_match_{match['id']}"
        )
    kb_builder.adjust(1)
    kb_builder.row(InlineKeyboardButton(text=LEXICON_RU["admin_cancel"], callback_data="admin_cancel"))
    return kb_builder.as_markup()


def admin_confirm_points_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Продолжить", callback_data="admin_next_player")
    kb_builder.button(text=LEXICON_RU["admin_cancel"], callback_data="admin_cancel")
    kb_builder.adjust(2)
    return kb_builder.as_markup()
