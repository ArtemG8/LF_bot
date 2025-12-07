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


def admin_main_menu_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_manage_players_button"], callback_data="admin_manage_players"),
        InlineKeyboardButton(text=LEXICON_RU["admin_manage_matches_button"], callback_data="admin_manage_matches"),
        width=2
    )
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_score_matches_button"], callback_data="admin_score_matches"),
        width=1
    )
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_change_password_button"], callback_data="admin_change_password"),
        InlineKeyboardButton(text=LEXICON_RU["admin_exit_button"], callback_data="admin_exit"),
        width=2
    )
    return kb_builder.as_markup()


def admin_player_management_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_add_player_button"], callback_data="admin_add_player"),
        InlineKeyboardButton(text=LEXICON_RU["admin_edit_player_button"], callback_data="admin_edit_player"),
        width=2
    )
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_delete_player_button"], callback_data="admin_delete_player"),
        width=1
    )
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_back_to_admin_menu"], callback_data="admin_back_to_main_menu"),
        width=1
    )
    return kb_builder.as_markup()


def admin_match_management_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_add_match_button"], callback_data="admin_add_match"),
        InlineKeyboardButton(text=LEXICON_RU["admin_manage_matches_button"], callback_data="admin_edit_matches"),
        # Переименовал для ясности
        width=2
    )
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_back_to_admin_menu"], callback_data="admin_back_to_main_menu"),
        width=1
    )
    return kb_builder.as_markup()


def create_players_list_keyboard(players: List[dict], callback_prefix: str) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for player in players:
        kb_builder.button(
            text=f"{player['name']} ({Config.POSITIONS.get(player['position'], player['position'])})",
            callback_data=f"{callback_prefix}_{player['id']}"
        )
    kb_builder.adjust(1)
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_cancel_admin_flow"], callback_data="admin_cancel_admin_flow"))
    return kb_builder.as_markup()


def create_positions_selection_keyboard(callback_prefix: str = "admin_select_position") -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for position_key, position_text in Config.POSITIONS.items():
        kb_builder.button(
            text=position_text,
            callback_data=f"{callback_prefix}_{position_key}"
        )
    kb_builder.adjust(2)
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_cancel_admin_flow"], callback_data="admin_cancel_admin_flow"))
    return kb_builder.as_markup()


def create_matches_list_keyboard(matches: List[dict], callback_prefix: str) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for match in matches:
        date_str = match['match_datetime'].strftime("%d.%m.%Y %H:%M")
        kb_builder.button(
            text=f"{date_str} - {match['opponent']}",
            callback_data=f"{callback_prefix}_{match['id']}"
        )
    kb_builder.adjust(1)
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_cancel_admin_flow"], callback_data="admin_cancel_admin_flow"))
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
    kb_builder.row(
        InlineKeyboardButton(text=LEXICON_RU["admin_cancel_admin_flow"], callback_data="admin_cancel_admin_flow"))
    return kb_builder.as_markup()


def admin_confirm_points_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Продолжить", callback_data="admin_next_player")
    kb_builder.button(text=LEXICON_RU["admin_cancel_admin_flow"], callback_data="admin_cancel_admin_flow")
    kb_builder.adjust(2)
    return kb_builder.as_markup()


def admin_confirm_delete_keyboard(player_id: int) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Да, удалить", callback_data=f"confirm_delete_player_{player_id}")
    kb_builder.button(text="Отмена", callback_data="admin_cancel_admin_flow")
    kb_builder.adjust(2)
    return kb_builder.as_markup()
