from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Tuple

from lexicon import LEXICON_RU


def create_inline_kb(
        width: int,
        *args: str,
        **kwargs: str
) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    buttons: List[InlineKeyboardButton] = []

    if args:
        for button_text in args:
            buttons.append(InlineKeyboardButton(text=button_text, callback_data=button_text))
    if kwargs:
        for button_text, callback_data in kwargs.items():
            buttons.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


def create_pagination_kb(
        current_page: int, total_pages: int, callback_prefix: str
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if current_page > 1:
        builder.button(text="⬅️", callback_data=f"{callback_prefix}_page_{current_page - 1}")
    builder.button(text=f"{current_page}/{total_pages}", callback_data="current_page_info")
    if current_page < total_pages:
        builder.button(text="➡️", callback_data=f"{callback_prefix}_page_{current_page + 1}")
    builder.adjust(3)
    return builder.as_markup()


def create_players_keyboard(players: List[Dict], selected_player_ids: List[int]) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for player in players:
        text = f"✅ {player['name']}" if player['id'] in selected_player_ids else player['name']
        kb_builder.button(
            text=text,
            callback_data=f"player_select_{player['id']}"
        )
    kb_builder.adjust(2)
    kb_builder.row(InlineKeyboardButton(text=LEXICON_RU["back_to_pickteam_button"], callback_data="back_to_pickteam"),
                   width=1)
    return kb_builder.as_markup()


def create_remove_players_keyboard(selected_players_names: List[Tuple[int, str]]) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for player_id, player_name in selected_players_names:
        kb_builder.button(
            text=player_name,
            callback_data=f"player_remove_{player_id}"
        )
    kb_builder.adjust(2)
    kb_builder.row(InlineKeyboardButton(text="Отмена", callback_data="cancel_remove_player"))
    return kb_builder.as_markup()
