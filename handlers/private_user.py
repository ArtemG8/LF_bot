import datetime
from datetime import timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from collections import defaultdict  # NEW: Import defaultdict

from config import Config
from lexicon import LEXICON_RU
from keyboards import (
    main_menu_keyboard, pickteam_positions_keyboard,
    create_players_keyboard, create_remove_players_keyboard,
    admin_main_menu_keyboard, admin_matches_to_score_keyboard,
    admin_player_management_keyboard, create_players_list_keyboard,
    create_positions_selection_keyboard, admin_match_management_keyboard,
    create_matches_list_keyboard, admin_confirm_delete_keyboard,
    admin_confirm_delete_all_players_keyboard, match_results_keyboard,
    match_details_keyboard, notifications_keyboard, admin_confirm_notification_keyboard
)
from database import Database
from states import PickTeamStates, AdminStates

router = Router()


async def send_main_menu(message: Message, text: str = LEXICON_RU["welcome"]):
    print(f"DEBUG: send_main_menu called for user {message.from_user.id}")
    await message.answer(text=text, reply_markup=main_menu_keyboard())


def format_timedelta(td: timedelta) -> str:
    days = td.days
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    parts = []
    if days > 0:
        parts.append(f"{days} д.")
    if hours > 0:
        parts.append(f"{hours} ч.")
    if minutes > 0:
        parts.append(f"{minutes} мин.")
    return " ".join(parts) if parts else "менее минуты"


# REWRITTEN: get_team_display_text to group and order players
async def get_team_display_text(player_ids: list, db: Database) -> str:
    if not player_ids:
        return "Ваш состав пуст."

    # Fetch all player details for the selected IDs, ordered by position and then order_index
    async with db.pool.acquire() as conn:
        players = await conn.fetch(
            """
            SELECT name, position, order_index
            FROM players
            WHERE id = ANY($1::int[])
            ORDER BY position, order_index
            """,
            player_ids
        )

    # Group players by position
    grouped_players = defaultdict(list)
    for player in players:
        grouped_players[player['position']].append(player['name'])

    display_text_parts = ["Ваш текущий состав:"]

    # Define the desired order of positions for display
    # This order should align with how players are grouped in NEW_PLAYERS_DATA
    position_keys_ordered = ["goalkeeper", "defender", "midfielder", "forward"]

    for position_key in position_keys_ordered:
        if grouped_players[position_key]:
            position_display_name = Config.POSITIONS.get(position_key, position_key.capitalize())
            display_text_parts.append(f"\n{position_display_name}:")
            for player_name in grouped_players[position_key]:
                display_text_parts.append(f"• {player_name}")

    return "\n".join(display_text_parts)


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database):
    print(f"DEBUG: cmd_start called for user {message.from_user.id}")
    user = await db.register_user(message.from_user.id, message.from_user.username or f"user_{message.from_user.id}")
    if user:
        await send_main_menu(message, LEXICON_RU["welcome"])
    else:
        await message.answer(LEXICON_RU["error_general"])


@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu_handler(callback: CallbackQuery, state: FSMContext, db: Database):
    # Логика сохранения последнего состава при выходе из PickTeamStates
    current_state = await state.get_state()
    if current_state and current_state.startswith("PickTeamStates"):
        data = await state.get_data()
        selected_players_ids: list = data.get("selected_players", [])
        user_id = (await db.get_user(callback.from_user.id))['id']
        if selected_players_ids:
            await db.save_last_selected_team(user_id, selected_players_ids)

    await state.clear()
    await callback.message.edit_text(LEXICON_RU["welcome"], reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(Command("pickteam"))
@router.callback_query(F.data == "pickteam")
async def cmd_pickteam(event: Message | CallbackQuery, state: FSMContext, db: Database):
    chat_id = event.from_user.id
    user_data = await db.get_user(chat_id)
    user_id = user_data['id']

    next_match = await db.get_next_match()
    if not next_match:
        await event.answer(LEXICON_RU["no_upcoming_matches"])
        return

    match_id = next_match['id']
    deadline = next_match['match_datetime'] - timedelta(minutes=1)

    if datetime.datetime.now() > deadline:
        await event.answer(LEXICON_RU["deadline_passed"],
                           show_alert=True if isinstance(event, CallbackQuery) else False)
        if isinstance(event, CallbackQuery):
            await event.message.edit_reply_markup(reply_markup=None)
        return

    current_team = await db.get_user_team(user_id, match_id)
    player_ids = current_team['player_ids'] if current_team else []

    if not player_ids:
        player_ids = user_data.get('last_selected_team_ids', [])

    await state.set_state(PickTeamStates.choosing_position)
    await state.update_data(
        match_id=match_id,
        selected_players=player_ids
    )

    selected_count = len(player_ids)
    text = LEXICON_RU["pickteam_intro"] + f"\n{LEXICON_RU['picked_players_count'].format(selected_count)}"
    text += "\n\n" + await get_team_display_text(player_ids, db)

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=pickteam_positions_keyboard(selected_count))
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=pickteam_positions_keyboard(selected_count))
        await event.answer()


@router.callback_query(F.data == "back_to_pickteam", StateFilter(PickTeamStates.choosing_player))
async def back_to_pickteam_from_players(callback: CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    selected_players_ids: list = data.get("selected_players", [])

    selected_count = len(selected_players_ids)
    text = LEXICON_RU["pickteam_intro"] + f"\n{LEXICON_RU['picked_players_count'].format(selected_count)}"
    text += "\n\n" + await get_team_display_text(selected_players_ids, db)

    await state.set_state(PickTeamStates.choosing_position)
    await callback.message.edit_text(
        text=text,
        reply_markup=pickteam_positions_keyboard(selected_count)
    )
    await callback.answer()


@router.message(Command("myteam"))
@router.callback_query(F.data == "myteam")
async def cmd_myteam(event: Message | CallbackQuery, db: Database):
    chat_id = event.from_user.id
    user_id = (await db.get_user(chat_id))['id']

    next_match = await db.get_next_match()
    if not next_match:
        await event.answer(LEXICON_RU["no_upcoming_matches"])
        return

    match_id = next_match['id']
    # Use the new get_team_display_text for consistent formatting
    current_team = await db.get_user_team(user_id, match_id)
    player_ids = current_team['player_ids'] if current_team else []

    if player_ids:
        text = await get_team_display_text(player_ids, db)
    else:
        text = LEXICON_RU["team_not_found"]

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=main_menu_keyboard())
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=main_menu_keyboard())
        await event.answer()


@router.message(Command("schedule"))
@router.callback_query(F.data == "schedule")
async def cmd_schedule(event: Message | CallbackQuery, db: Database):
    next_match = await db.get_next_match()
    text = ""

    if next_match:
        match_dt = next_match['match_datetime']
        deadline_dt = match_dt - timedelta(minutes=1)
        now = datetime.datetime.now()

        time_left = match_dt - now
        deadline_countdown = deadline_dt - now

        text += LEXICON_RU["upcoming_match_info"].format(
            opponent=next_match['opponent'],
            date=match_dt.strftime("%d.%m.%Y"),
            time=match_dt.strftime("%H:%M"),
            time_left=format_timedelta(time_left),
            deadline_time=deadline_dt.strftime("%d.%m.%Y %H:%M"),
            deadline_countdown=format_timedelta(deadline_countdown)
        )
    else:
        text += LEXICON_RU["no_upcoming_matches"]

    matches_for_month = await db.get_matches_for_month()
    if matches_for_month:
        text += LEXICON_RU["matches_for_month"]
        for match in matches_for_month:
            match_dt = match['match_datetime']
            text += LEXICON_RU["match_entry"].format(
                date=match_dt.strftime("%d.%m"),
                opponent=match['opponent']
            ) + "\n"

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=main_menu_keyboard())
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=main_menu_keyboard())
        await event.answer()


@router.callback_query(F.data == "match_results")
@router.callback_query(F.data.startswith("match_results_page_"))
async def cmd_match_results(callback: CallbackQuery, db: Database):
    page = 0
    if callback.data.startswith("match_results_page_"):
        page = int(callback.data.split("_")[-1])

    offset = page * Config.MATCHES_PER_PAGE
    limit = Config.MATCHES_PER_PAGE

    result = await db.get_finished_matches_paginated(offset, limit)
    matches = result["matches"]
    total_count = result["total_count"]

    text = LEXICON_RU["finished_matches_header"]

    if not matches:
        text += "\n" + LEXICON_RU["no_finished_matches"]
    else:
        # No need to list matches here, as each match will have a dedicated button
        text += "\nВыберите матч для просмотра деталей:"

    total_pages = (total_count + Config.MATCHES_PER_PAGE - 1) // Config.MATCHES_PER_PAGE

    await callback.message.edit_text(
        text=text,
        reply_markup=match_results_keyboard(matches, page, total_pages)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("match_details_"))
async def cmd_match_details(callback: CallbackQuery, db: Database):
    data_parts = callback.data.split("_")
    match_id = int(data_parts[2])
    current_page_from_callback = int(data_parts[3]) if len(data_parts) > 3 else 0 # Извлекаем номер страницы
    user_id = (await db.get_user(callback.from_user.id))['id']

    match_details = await db.get_match_details(match_id)
    if not match_details:
        await callback.answer(LEXICON_RU["admin_match_not_found"], show_alert=True)
        return

    player_data = await db.get_match_player_scores_and_user_teams(match_id, user_id)
    player_scores = player_data["player_scores"]
    user_team_player_ids = player_data["user_team_player_ids"]

    date_str = match_details['match_datetime'].strftime("%d.%m.%Y")
    time_str = match_details['match_datetime'].strftime("%H:%M")

    text_parts = [
        LEXICON_RU["match_results_details_header"].format(
            opponent=match_details['opponent'], date=date_str, time=time_str
        ),
        "\n"
    ]

    user_total_score = 0.0
    if player_scores:
        text_parts.append("Очки игроков:")
        for i, player in enumerate(player_scores):
            emoji = "🌟" if player['player_id'] in user_team_player_ids else ""
            text_parts.append(
                LEXICON_RU["match_player_score_entry"].format(
                    i + 1,
                    player_name=player['name'],
                    points=round(player['points'], 2),
                    emoji=emoji
                )
            )
            if player['player_id'] in user_team_player_ids:
                user_total_score += player['points']
        text_parts.append(f"\n{LEXICON_RU['match_total_user_score'].format(score=round(user_total_score, 2))}")
    else:
        text_parts.append("Нет данных по очкам игроков для этого матча.")
        # If user team exists but no scores, display that.
        if user_team_player_ids:
             user_team_names = await db.get_player_names_from_ids(user_team_player_ids)
             text_parts.append(f"Ваша команда на этот матч: {', '.join(user_team_names)}")
        else:
            text_parts.append(LEXICON_RU["match_no_team_selected"])

    # Determine the current page for returning to the match list
    # This assumes that the `match_details_` callback is always called from a paginated list
    # It would be better to pass the current page explicitly in the callback data.
    # For now, we'll try to infer it or default to 0.
    # This might require a state machine or more complex callback data.
    # For simplicity, we'll use a default of 0 for now.
    # A more robust solution would involve passing the `page` argument from `cmd_match_results`
    # to the `match_details_` callback.
    # For now, we assume the user is coming from the first page of results.

    await callback.message.edit_text(
        text="\n".join(text_parts),
        reply_markup=match_details_keyboard(match_id, current_page_from_callback)
    )
    await callback.answer()


@router.callback_query(F.data == "leaderboard")
async def cmd_leaderboard(event: Message | CallbackQuery, db: Database):
    leaderboard_data = await db.get_leaderboard()
    text = LEXICON_RU["leaderboard_header"]
    if leaderboard_data:
        for i, entry in enumerate(leaderboard_data):
            text += LEXICON_RU["leaderboard_entry"].format(
                i + 1,
                username=entry['username'],
                score=round(entry['total_score'], 2)
            ) + "\n"
    else:
        text += "Пока нет данных для общей таблицы лидеров."

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=main_menu_keyboard())
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=main_menu_keyboard())
        await event.answer()


@router.callback_query(F.data == "weekly_leaderboard")
async def cmd_weekly_leaderboard(callback: CallbackQuery, db: Database):
    leaderboard_data = await db.get_weekly_leaderboard()
    text = LEXICON_RU["weekly_leaderboard_header"]
    if leaderboard_data:
        for i, entry in enumerate(leaderboard_data):
            text += LEXICON_RU["leaderboard_entry"].format(
                i + 1,
                username=entry['username'],
                score=round(entry['weekly_score'], 2)
            ) + "\n"
    else:
        text += "Пока нет данных для недельного рейтинга."

    await callback.message.edit_text(text=text, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(Command("resetteam"))
@router.callback_query(F.data == "resetteam")
async def cmd_resetteam(event: Message | CallbackQuery, db: Database):
    chat_id = event.from_user.id
    user_id = (await db.get_user(chat_id))['id']

    next_match = await db.get_next_match()
    if not next_match:
        await event.answer(LEXICON_RU["no_upcoming_matches"])
        return

    match_id = next_match['id']
    deadline = next_match['match_datetime'] - timedelta(minutes=1)

    if datetime.datetime.now() > deadline:
        await event.answer(LEXICON_RU["deadline_passed"],
                           show_alert=True if isinstance(event, CallbackQuery) else False)
        if isinstance(event, CallbackQuery):
            await event.message.edit_reply_markup(reply_markup=None)
        return

    user_team = await db.get_user_team(user_id, match_id)
    if user_team:
        await db.delete_user_team(user_id, match_id)
        text = LEXICON_RU["resetteam_success"]
    else:
        text = LEXICON_RU["resetteam_no_team"]

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=main_menu_keyboard())
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=main_menu_keyboard())
        await event.answer()


@router.callback_query(F.data.startswith("select_position_"), StateFilter(PickTeamStates.choosing_position))
async def process_position_selection(callback: CallbackQuery, state: FSMContext, db: Database):
    position_key = callback.data.split("_")[-1]
    data = await state.get_data()
    selected_players_ids: list = data.get("selected_players", [])

    players_by_position = await db.get_players_by_position(position_key)

    await state.set_state(PickTeamStates.choosing_player)
    await state.update_data(current_position_players=players_by_position)

    text = f"{Config.POSITIONS[position_key]}\n\n" + await get_team_display_text(selected_players_ids, db)
    await callback.message.edit_text(
        text=text,
        reply_markup=create_players_keyboard(players_by_position, selected_players_ids)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("player_select_"), StateFilter(PickTeamStates.choosing_player))
async def process_player_selection(callback: CallbackQuery, state: FSMContext, db: Database):
    player_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    selected_players_ids: list = data.get("selected_players", [])

    if player_id in selected_players_ids:
        selected_players_ids.remove(player_id)
    else:
        if len(selected_players_ids) < 5:
            selected_players_ids.append(player_id)
        else:
            await callback.answer("Вы можете выбрать не более 5 игроков.", show_alert=True)
            return

    await state.update_data(selected_players=selected_players_ids)

    selected_count = len(selected_players_ids)
    text = LEXICON_RU["pickteam_intro"] + f"\n{LEXICON_RU['picked_players_count'].format(selected_count)}"
    text += "\n\n" + await get_team_display_text(selected_players_ids, db)

    await state.set_state(PickTeamStates.choosing_position)
    await callback.message.edit_text(
        text=text,
        reply_markup=pickteam_positions_keyboard(selected_count)
    )
    await callback.answer()


@router.callback_query(F.data == "remove_player", StateFilter(PickTeamStates.choosing_position))
async def process_remove_player_request(callback: CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    selected_players_ids: list = data.get("selected_players", [])

    if not selected_players_ids:
        await callback.answer(LEXICON_RU["pickteam_no_players_to_remove"], show_alert=True)
        return

    # Fetch all players sorted by order_index for the map
    all_players = await db.get_all_players_sorted()
    player_names_map = {p['id']: p['name'] for p in all_players}
    players_to_remove = [(p_id, player_names_map.get(p_id, "Неизвестный игрок")) for p_id in selected_players_ids]

    await state.set_state(PickTeamStates.removing_player)
    await callback.message.edit_text(
        text=LEXICON_RU["pickteam_choose_player_to_remove"],
        reply_markup=create_remove_players_keyboard(players_to_remove)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("player_remove_"), StateFilter(PickTeamStates.removing_player))
async def process_player_removal(callback: CallbackQuery, state: FSMContext, db: Database):
    player_id_to_remove = int(callback.data.split("_")[-1])
    data = await state.get_data()
    selected_players_ids: list = data.get("selected_players", [])

    if player_id_to_remove in selected_players_ids:
        selected_players_ids.remove(player_id_to_remove)
        await state.update_data(selected_players=selected_players_ids)
        removed_player_info = await db.get_player_by_id(player_id_to_remove)
        player_name = removed_player_info['name'] if removed_player_info else "игрок"
        await callback.answer(LEXICON_RU["pickteam_removed_player"].format(player_name))
    else:
        await callback.answer("Этого игрока нет в вашем составе.", show_alert=True)

    selected_count = len(selected_players_ids)
    text = LEXICON_RU["pickteam_intro"] + f"\n{LEXICON_RU['picked_players_count'].format(selected_count)}"
    text += "\n\n" + await get_team_display_text(selected_players_ids, db)

    await state.set_state(PickTeamStates.choosing_position)
    await callback.message.edit_text(
        text=text,
        reply_markup=pickteam_positions_keyboard(selected_count)
    )


@router.callback_query(F.data == "cancel_remove_player", StateFilter(PickTeamStates.removing_player))
async def cancel_player_removal(callback: CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    selected_players_ids: list = data.get("selected_players", [])
    selected_count = len(selected_players_ids)
    text = LEXICON_RU["pickteam_intro"] + f"\n{LEXICON_RU['picked_players_count'].format(selected_count)}"
    text += "\n\n" + await get_team_display_text(selected_players_ids, db)

    await state.set_state(PickTeamStates.choosing_position)
    await callback.message.edit_text(
        text=text,
        reply_markup=pickteam_positions_keyboard(selected_count)
    )
    await callback.answer("Отмена удаления игрока.")


@router.callback_query(F.data == "confirm_team", StateFilter(PickTeamStates.choosing_position))
async def process_confirm_team(callback: CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    selected_players_ids: list = data.get("selected_players", [])
    match_id = data.get("match_id")
    chat_id = callback.from_user.id
    user_id = (await db.get_user(chat_id))['id']

    if len(selected_players_ids) != 5:
        await callback.answer(LEXICON_RU["pickteam_not_5_players_error"], show_alert=True)
        return

    await db.save_user_team(user_id, match_id, selected_players_ids)
    await db.save_last_selected_team(user_id, selected_players_ids) # Сохраняем как последний выбранный состав
    await state.clear()

    text = LEXICON_RU["team_picked_success"] + "\n\n" + await get_team_display_text(selected_players_ids, db)
    await callback.message.edit_text(text=text, reply_markup=main_menu_keyboard())
    await callback.answer("Состав сохранен!")


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    # if message.from_user.id != Config.ADMIN_ID:
    #     await message.answer(LEXICON_RU["admin_unknown_command"])
    #     return

    await state.set_state(AdminStates.waiting_for_password)
    await message.answer(LEXICON_RU["admin_enter_password"])


@router.message(StateFilter(AdminStates.waiting_for_password))
async def process_admin_password(message: Message, state: FSMContext, db: Database):
    entered_password = message.text
    admin_password = await db.get_admin_setting('admin_password')

    if entered_password == admin_password:
        await state.set_state(AdminStates.admin_menu)
        await message.answer(LEXICON_RU["admin_panel_menu"], reply_markup=admin_main_menu_keyboard())
    else:
        await message.answer(LEXICON_RU["admin_wrong_password"])


@router.callback_query(F.data == "admin_back_to_main_menu", StateFilter(AdminStates))
async def admin_back_to_main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.admin_menu)
    await callback.message.edit_text(LEXICON_RU["admin_panel_menu"], reply_markup=admin_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_manage_players", StateFilter(AdminStates.admin_menu))
async def admin_manage_players_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.managing_players)
    await callback.message.edit_text(LEXICON_RU["admin_player_management_menu"],
                                     reply_markup=admin_player_management_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_view_players", StateFilter(AdminStates.managing_players))
async def admin_view_players(callback: CallbackQuery, db: Database):
    all_players = await db.get_all_players_sorted()
    text = LEXICON_RU["admin_view_all_players_header"] + "\n\n"
    if all_players:
        for player in all_players:
            text += LEXICON_RU["admin_player_entry_view"].format(
                id=player['id'],
                name=player['name'],
                position=Config.POSITIONS.get(player['position'], player['position'])
            ) + "\n"
    else:
        text += LEXICON_RU["admin_no_players_found"]

    await callback.message.edit_text(text, reply_markup=admin_player_management_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_remove_all_players", StateFilter(AdminStates.managing_players))
async def admin_remove_all_players_confirm(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.confirming_delete_all_players)
    await callback.message.edit_text(
        LEXICON_RU["admin_confirm_remove_all_players"],
        reply_markup=admin_confirm_delete_all_players_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_delete_all_players_yes",
                       StateFilter(AdminStates.confirming_delete_all_players))
async def admin_execute_remove_all_players(callback: CallbackQuery, state: FSMContext, db: Database):
    success = await db.delete_all_players()
    if success:
        await callback.message.edit_text(LEXICON_RU["admin_all_players_removed_success"],
                                         reply_markup=admin_player_management_keyboard())
    else:
        await callback.message.edit_text(LEXICON_RU["error_general"], reply_markup=admin_player_management_keyboard())
    await state.set_state(AdminStates.managing_players)
    await callback.answer()


@router.callback_query(F.data == "admin_add_player", StateFilter(AdminStates.managing_players))
async def admin_add_player_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.adding_player_name)
    await callback.message.edit_text(LEXICON_RU["admin_enter_player_name"])
    await callback.answer()


@router.message(StateFilter(AdminStates.adding_player_name))
async def admin_process_player_name(message: Message, state: FSMContext):
    player_name = message.text
    await state.update_data(new_player_name=player_name)
    await state.set_state(AdminStates.adding_player_position)
    await message.answer(LEXICON_RU["admin_choose_player_position"], reply_markup=create_positions_selection_keyboard())


@router.callback_query(F.data.startswith("admin_select_position_"), StateFilter(AdminStates.adding_player_position))
async def admin_process_player_position(callback: CallbackQuery, state: FSMContext, db: Database):
    position_key = callback.data.split("_")[-1]
    data = await state.get_data()
    player_name = data.get("new_player_name")

    if player_name and position_key:
        player = await db.add_player(player_name, position_key)
        if player:
            await callback.message.edit_text(
                LEXICON_RU["admin_player_added_success"].format(
                    player_name=player_name, position_name=Config.POSITIONS[position_key]
                ),
                reply_markup=admin_player_management_keyboard()
            )
        else:
            await callback.message.edit_text(LEXICON_RU["admin_player_already_exists"],
                                             reply_markup=admin_player_management_keyboard())
    else:
        await callback.message.edit_text(LEXICON_RU["error_general"], reply_markup=admin_player_management_keyboard())
    await state.set_state(AdminStates.managing_players)
    await callback.answer()


@router.callback_query(F.data == "admin_edit_player", StateFilter(AdminStates.managing_players))
async def admin_edit_player_start(callback: CallbackQuery, state: FSMContext, db: Database):
    players = await db.get_all_players_sorted()
    if not players:
        await callback.answer(LEXICON_RU["admin_no_players_found"], show_alert=True)
        return

    await state.set_state(AdminStates.selecting_player_to_edit)
    await callback.message.edit_text(LEXICON_RU["admin_select_player_to_edit"],
                                     reply_markup=create_players_list_keyboard(players, "admin_selected_player_edit"))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_selected_player_edit_"),
                       StateFilter(AdminStates.selecting_player_to_edit))
async def admin_selected_player_for_edit(callback: CallbackQuery, state: FSMContext, db: Database):
    player_id = int(callback.data.split("_")[-1])
    player_details = await db.get_player_by_id(player_id)
    if not player_details:
        await callback.answer(LEXICON_RU["admin_player_not_found"], show_alert=True)
        await state.set_state(AdminStates.managing_players)
        await callback.message.edit_text(LEXICON_RU["admin_player_management_menu"],
                                         reply_markup=admin_player_management_keyboard())
        return

    await state.update_data(editing_player_id=player_id, original_player_name=player_details['name'])
    await state.set_state(AdminStates.editing_player_name)
    await callback.message.edit_text(
        LEXICON_RU["admin_edit_player_name_prompt"].format(current_name=player_details['name']))
    await callback.answer()


@router.message(StateFilter(AdminStates.editing_player_name))
async def admin_process_edited_player_name(message: Message, state: FSMContext):
    new_name = message.text
    await state.update_data(edited_player_name=new_name)
    await state.set_state(AdminStates.editing_player_position)
    data = await state.get_data()
    original_name = data.get('original_player_name', '')
    await message.answer(LEXICON_RU["admin_edit_player_position_prompt"].format(current_name=original_name),
                         reply_markup=create_positions_selection_keyboard(callback_prefix="admin_edited_position"))


@router.callback_query(F.data.startswith("admin_edited_position_"), StateFilter(AdminStates.editing_player_position))
async def admin_process_edited_player_position(callback: CallbackQuery, state: FSMContext, db: Database):
    new_position = callback.data.split("_")[-1]
    data = await state.get_data()
    player_id = data.get("editing_player_id")
    new_name = data.get("edited_player_name")

    if player_id and new_name and new_position:
        success = await db.update_player(player_id, new_name, new_position)
        if success:
            await callback.message.edit_text(LEXICON_RU["admin_player_updated_success"].format(player_name=new_name),
                                             reply_markup=admin_player_management_keyboard())
        else:
            await callback.message.edit_text(LEXICON_RU["error_general"],
                                             reply_markup=admin_player_management_keyboard())
    else:
        await callback.message.edit_text(LEXICON_RU["error_general"], reply_markup=admin_player_management_keyboard())
    await state.set_state(AdminStates.managing_players)
    await callback.answer()


@router.callback_query(F.data == "admin_delete_player", StateFilter(AdminStates.managing_players))
async def admin_delete_player_start(callback: CallbackQuery, state: FSMContext, db: Database):
    players = await db.get_all_players_sorted()
    if not players:
        await callback.answer(LEXICON_RU["admin_no_players_found"], show_alert=True)
        return

    await state.set_state(AdminStates.selecting_player_to_delete)
    await callback.message.edit_text(LEXICON_RU["admin_select_player_to_delete"],
                                     reply_markup=create_players_list_keyboard(players, "admin_selected_player_delete"))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_selected_player_delete_"),
                       StateFilter(AdminStates.selecting_player_to_delete))
async def admin_confirm_delete_player(callback: CallbackQuery, state: FSMContext, db: Database):
    player_id = int(callback.data.split("_")[-1])
    player_details = await db.get_player_by_id(player_id)
    if not player_details:
        await callback.answer(LEXICON_RU["admin_player_not_found"], show_alert=True)
        await state.set_state(AdminStates.managing_players)
        await callback.message.edit_text(LEXICON_RU["admin_player_management_menu"],
                                         reply_markup=admin_player_management_keyboard())
        return

    await state.update_data(player_to_delete_id=player_id, player_to_delete_name=player_details['name'])
    await state.set_state(AdminStates.confirming_player_delete)
    await callback.message.edit_text(
        LEXICON_RU["admin_confirm_delete_player"].format(player_name=player_details['name']),
        reply_markup=admin_confirm_delete_keyboard(player_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_player_"), StateFilter(AdminStates.confirming_player_delete))
async def admin_execute_delete_player(callback: CallbackQuery, state: FSMContext, db: Database):
    player_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    player_name = data.get('player_to_delete_name', 'игрока')

    success = await db.delete_player(player_id)
    if success:
        await callback.message.edit_text(LEXICON_RU["admin_player_deleted_success"].format(player_name=player_name),
                                         reply_markup=admin_player_management_keyboard())
    else:
        await callback.message.edit_text(LEXICON_RU["error_general"], reply_markup=admin_player_management_keyboard())
    await state.set_state(AdminStates.managing_players)
    await callback.answer()


@router.callback_query(F.data == "admin_manage_matches", StateFilter(AdminStates.admin_menu))
async def admin_manage_matches_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.managing_matches)
    await callback.message.edit_text(LEXICON_RU["admin_panel_menu"], reply_markup=admin_match_management_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_add_match", StateFilter(AdminStates.managing_matches))
async def admin_add_match_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.adding_match_opponent)
    await callback.message.edit_text(LEXICON_RU["admin_enter_match_opponent"])
    await callback.answer()


@router.message(StateFilter(AdminStates.adding_match_opponent))
async def admin_process_match_opponent_add(message: Message, state: FSMContext):
    opponent = message.text
    await state.update_data(new_match_opponent=opponent)
    await state.set_state(AdminStates.adding_match_datetime)
    await message.answer(LEXICON_RU["admin_enter_match_datetime"])


@router.message(StateFilter(AdminStates.adding_match_datetime))
async def admin_process_match_datetime_add(message: Message, state: FSMContext, db: Database):
    datetime_str = message.text
    try:
        match_dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        if match_dt < datetime.datetime.now():
            await message.answer(
                "Дата и время матча не могут быть в прошлом. Пожалуйста, введите корректное будущее время.")
            return
    except ValueError:
        await message.answer(LEXICON_RU["admin_invalid_datetime_format"])
        return

    data = await state.get_data()
    opponent = data.get("new_match_opponent")

    if opponent:
        success = await db.add_match(opponent, match_dt)
        if success:
            await message.answer(
                LEXICON_RU["admin_match_added_success"].format(
                    opponent=opponent,
                    date=match_dt.strftime("%d.%m.%Y"),
                    time=match_dt.strftime("%H:%M")
                ),
                reply_markup=admin_match_management_keyboard()
            )
        else:
            await message.answer(LEXICON_RU["admin_match_already_exists"],
                                 reply_markup=admin_match_management_keyboard())
    else:
        await message.answer(LEXICON_RU["error_general"], reply_markup=admin_match_management_keyboard())

    await state.set_state(AdminStates.managing_matches)


@router.callback_query(F.data == "admin_edit_matches", StateFilter(AdminStates.managing_matches))
async def admin_edit_matches_start(callback: CallbackQuery, state: FSMContext, db: Database):
    upcoming_matches = await db.get_upcoming_matches()
    if not upcoming_matches:
        await callback.answer(LEXICON_RU["admin_no_matches_found"], show_alert=True)
        return

    await state.set_state(AdminStates.selecting_match_to_edit)
    await callback.message.edit_text(LEXICON_RU["admin_select_match_to_edit"],
                                     reply_markup=create_matches_list_keyboard(upcoming_matches,
                                                                               "admin_selected_match_edit"))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_selected_match_edit_"),
                       StateFilter(AdminStates.selecting_match_to_edit))
async def admin_selected_match_for_edit(callback: CallbackQuery, state: FSMContext, db: Database):
    match_id = int(callback.data.split("_")[-1])
    match_details = await db.get_match_details(match_id)
    if not match_details:
        await callback.answer(LEXICON_RU["admin_match_not_found"], show_alert=True)
        await state.set_state(AdminStates.managing_matches)
        await callback.message.edit_text(LEXICON_RU["admin_panel_menu"], reply_markup=admin_match_management_keyboard())
        return

    await state.update_data(
        editing_match_id=match_id,
        original_match_opponent=match_details['opponent'],
        original_match_datetime=match_details['match_datetime']
    )

    date_str = match_details['match_datetime'].strftime("%d.%m.%Y")
    time_str = match_details['match_datetime'].strftime("%H:%M")

    await state.set_state(AdminStates.editing_match_opponent)
    await callback.message.edit_text(
        LEXICON_RU["admin_edit_match_opponent_prompt"].format(
            current_opponent=match_details['opponent'], current_date=date_str, current_time=time_str
        )
    )
    await callback.answer()


@router.message(StateFilter(AdminStates.editing_match_opponent))
async def admin_process_edited_match_opponent(message: Message, state: FSMContext):
    new_opponent = message.text
    await state.update_data(edited_match_opponent=new_opponent)
    await state.set_state(AdminStates.editing_match_datetime)
    data = await state.get_data()
    original_match_opponent = data.get('original_match_opponent')
    original_match_datetime: datetime.datetime = data.get('original_match_datetime')
    date_str = original_match_datetime.strftime("%d.%m.%Y")
    time_str = original_match_datetime.strftime("%H:%M")
    await message.answer(
        LEXICON_RU["admin_edit_match_datetime_prompt"].format(
            current_opponent=original_match_opponent, current_date=date_str, current_time=time_str
        )
    )


@router.message(StateFilter(AdminStates.editing_match_datetime))
async def admin_process_edited_match_datetime(message: Message, state: FSMContext, db: Database):
    datetime_str = message.text
    try:
        new_match_dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        if new_match_dt < datetime.datetime.now():
            await message.answer(
                "Дата и время матча не могут быть в прошлом. Пожалуйста, введите корректное будущее время.")
            return
    except ValueError:
        await message.answer(LEXICON_RU["admin_invalid_datetime_format"])
        return

    data = await state.get_data()
    match_id = data.get("editing_match_id")
    edited_opponent = data.get("edited_match_opponent")

    if match_id and edited_opponent and new_match_dt:
        success = await db.update_match(match_id, edited_opponent, new_match_dt)
        if success:
            await message.answer(
                LEXICON_RU["admin_match_updated_success"].format(
                    opponent=edited_opponent,
                    date=new_match_dt.strftime("%d.%m.%Y"),
                    time=new_match_dt.strftime("%H:%M")
                ),
                reply_markup=admin_match_management_keyboard()
            )
        else:
            await message.answer(LEXICON_RU["error_general"], reply_markup=admin_match_management_keyboard())
    else:
        await message.answer(LEXICON_RU["error_general"], reply_markup=admin_match_management_keyboard())
    await state.set_state(AdminStates.managing_matches)


@router.callback_query(F.data == "admin_score_matches", StateFilter(AdminStates.admin_menu))
async def admin_select_match_to_score_start(callback: CallbackQuery, state: FSMContext, db: Database):
    await state.set_state(AdminStates.selecting_match_to_score)
    finished_unscored_matches = await db.get_finished_unscored_matches()

    if not finished_unscored_matches:
        await callback.message.edit_text("Нет завершенных матчей, для которых нужно ввести очки.",
                                         reply_markup=admin_main_menu_keyboard())
        await state.set_state(AdminStates.admin_menu)
        return

    await callback.message.edit_text(
        LEXICON_RU["admin_select_match_to_score"],
        reply_markup=admin_matches_to_score_keyboard(finished_unscored_matches)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_score_match_"), StateFilter(AdminStates.selecting_match_to_score))
async def admin_select_match_for_scoring(callback: CallbackQuery, state: FSMContext, db: Database):
    match_id = int(callback.data.split("_")[-1])
    match_details = await db.get_match_details(match_id)

    if not match_details:
        await callback.answer(LEXICON_RU["admin_match_not_found"], show_alert=True)
        await state.set_state(AdminStates.admin_menu)
        await callback.message.edit_text(LEXICON_RU["admin_panel_menu"], reply_markup=admin_main_menu_keyboard())
        return

    all_players = await db.get_all_players_sorted()  # Now sorted by order_index
    # all_players.sort(key=lambda p: (p['position'], p['name'])) # This sort is no longer needed if using order_index

    await state.update_data(
        admin_current_match_id=match_id,
        admin_match_details=match_details,
        admin_players_to_score=all_players,
        admin_current_player_index=0,
        admin_player_points_data={}
    )
    await state.set_state(AdminStates.entering_player_points)

    current_player = all_players[0]
    date_str = match_details['match_datetime'].strftime("%d.%m.%Y")
    time_str = match_details['match_datetime'].strftime("%H:%M")

    await callback.message.edit_text(
        text=LEXICON_RU["admin_match_info_score"].format(
            opponent=match_details['opponent'], date=date_str, time=time_str
        ) + "\n\n" + LEXICON_RU["admin_enter_player_points"].format(player_name=current_player['name'])
    )
    await callback.answer()


@router.message(StateFilter(AdminStates.entering_player_points))
async def admin_process_player_points(message: Message, state: FSMContext, db: Database, bot: Bot):
    try:
        points = float(message.text.replace(',', '.'))
    except ValueError:
        await message.answer(LEXICON_RU["admin_invalid_points_format"])
        return

    data = await state.get_data()
    admin_players_to_score: list = data.get("admin_players_to_score", [])
    admin_current_player_index: int = data.get("admin_current_player_index", 0)
    admin_player_points_data: dict = data.get("admin_player_points_data", {})
    admin_current_match_id: int = data.get("admin_current_match_id")

    current_player = admin_players_to_score[admin_current_player_index]
    admin_player_points_data[current_player['id']] = points
    await message.answer(
        LEXICON_RU["admin_points_saved_success"].format(player_name=current_player['name'], points=points))

    admin_current_player_index += 1
    if admin_current_player_index < len(admin_players_to_score):
        next_player = admin_players_to_score[admin_current_player_index]
        await state.update_data(
            admin_current_player_index=admin_current_player_index,
            admin_player_points_data=admin_player_points_data
        )
        await message.answer(
            LEXICON_RU["admin_enter_player_points"].format(player_name=next_player['name'])
        )
    else:
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                for player_id, pts in admin_player_points_data.items():
                    await db.save_player_points(admin_current_match_id, player_id, pts)
                await db.update_user_scores_for_match(admin_current_match_id)

        await message.answer(LEXICON_RU["admin_all_points_entered"])
        # Сохраняем match_details в state для дальнейшей отправки уведомления
        match_details = data.get("admin_match_details")
        await state.update_data(admin_match_details=match_details)
        await state.set_state(AdminStates.entering_notification_message)
        await message.answer(LEXICON_RU["admin_prompt_notification_message"])


@router.message(StateFilter(AdminStates.entering_notification_message))
async def admin_process_notification_message(message: Message, state: FSMContext):
    additional_message = message.text if message.text != "-" else ""
    await state.update_data(admin_additional_notification_message=additional_message)

    data = await state.get_data()
    match_details = data.get("admin_match_details")

    opponent = match_details['opponent']
    date_str = match_details['match_datetime'].strftime("%d.%m.%Y")
    time_str = match_details['match_datetime'].strftime("%H:%M")

    base_notification_text = LEXICON_RU["notifications_match_scored_message"].format(
        opponent=opponent, date=date_str, time=time_str
    )
    if additional_message:
        preview_text = f"{additional_message}\n\n{base_notification_text}"
    else:
        preview_text = base_notification_text

    await state.set_state(AdminStates.confirming_notification_send)
    await message.answer(
        text=f"{LEXICON_RU['admin_confirm_send_notification']}\n\n{preview_text}",
        reply_markup=admin_confirm_notification_keyboard()
    )


@router.callback_query(F.data == "admin_send_notification_yes", StateFilter(AdminStates.confirming_notification_send))
async def admin_execute_send_notification(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    data = await state.get_data()
    match_details = data.get("admin_match_details")
    additional_message = data.get("admin_additional_notification_message", "")

    if match_details:
        opponent = match_details['opponent']
        date_str = match_details['match_datetime'].strftime("%d.%m.%Y")
        time_str = match_details['match_datetime'].strftime("%H:%M")
        base_notification_text = LEXICON_RU["notifications_match_scored_message"].format(
            opponent=opponent, date=date_str, time=time_str
        )
        if additional_message:
            final_notification_text = f"{additional_message}\n\n{base_notification_text}"
        else:
            final_notification_text = base_notification_text

        users_to_notify = await db.get_users_with_notifications_enabled()
        for user in users_to_notify:
            try:
                await bot.send_message(user['telegram_id'], final_notification_text, reply_markup=main_menu_keyboard())
            except Exception as e:
                print(f"Не удалось отправить уведомление пользователю {user['telegram_id']}: {e}")

    await state.clear()
    await callback.message.edit_text(LEXICON_RU["admin_notification_sent_success"], reply_markup=admin_main_menu_keyboard())
    await callback.answer()
    await state.set_state(AdminStates.admin_menu)


@router.callback_query(F.data == "admin_send_notification_no", StateFilter(AdminStates.confirming_notification_send))
async def admin_cancel_send_notification(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(LEXICON_RU["admin_notification_cancelled"], reply_markup=admin_main_menu_keyboard())
    await callback.answer()
    await state.set_state(AdminStates.admin_menu)


@router.callback_query(F.data == "admin_change_password", StateFilter(AdminStates.admin_menu))
async def admin_change_password_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.changing_password)
    await callback.message.edit_text(LEXICON_RU["admin_enter_new_password"])
    await callback.answer()


@router.message(StateFilter(AdminStates.changing_password))
async def admin_process_new_password(message: Message, state: FSMContext, db: Database):
    new_password = message.text
    await db.set_admin_setting('admin_password', new_password)
    await state.set_state(AdminStates.admin_menu)
    await message.answer(
        LEXICON_RU["admin_password_changed"].format(new_password=new_password),
        reply_markup=admin_main_menu_keyboard()
    )


@router.callback_query(F.data == "admin_exit", StateFilter(AdminStates.admin_menu))
async def admin_exit_panel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(LEXICON_RU["admin_exit_button"], reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_cancel_admin_flow", StateFilter(AdminStates))
async def admin_cancel_flow(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state.startswith("AdminStates:managing_players"):
        await state.set_state(AdminStates.managing_players)
        await callback.message.edit_text(LEXICON_RU["admin_player_management_menu"],
                                         reply_markup=admin_player_management_keyboard())
    elif current_state.startswith("AdminStates:managing_matches"):
        await state.set_state(AdminStates.managing_matches)
        await callback.message.edit_text(LEXICON_RU["admin_panel_menu"], reply_markup=admin_match_management_keyboard())
    else:
        await state.set_state(AdminStates.admin_menu)
        await callback.message.edit_text(LEXICON_RU["admin_cancel_admin_flow"], reply_markup=admin_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "notifications")
async def cmd_notifications(callback: CallbackQuery, db: Database):
    user = await db.get_user(callback.from_user.id)
    notifications_enabled = user['receive_notifications']

    status_text = LEXICON_RU["notifications_enabled"] if notifications_enabled else LEXICON_RU["notifications_disabled"]
    text = f"{LEXICON_RU['notifications_header']}\n\n{status_text}"

    await callback.message.edit_text(
        text=text,
        reply_markup=notifications_keyboard(notifications_enabled)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("notifications_toggle_"))
async def toggle_notifications(callback: CallbackQuery, db: Database):
    user_id = (await db.get_user(callback.from_user.id))['id']
    toggle_action = callback.data.split("_")[-1]
    new_preference = True if toggle_action == "on" else False

    await db.update_user_notification_preference(user_id, new_preference)

    status_message = LEXICON_RU["notifications_success_on"] if new_preference else LEXICON_RU["notifications_success_off"]

    user = await db.get_user(callback.from_user.id) # Re-fetch user to get updated preference
    notifications_enabled = user['receive_notifications']

    status_text = LEXICON_RU["notifications_enabled"] if notifications_enabled else LEXICON_RU["notifications_disabled"]
    text = f"{LEXICON_RU['notifications_header']}\n\n{status_text}"

    await callback.message.edit_text(
        text=text,
        reply_markup=notifications_keyboard(notifications_enabled)
    )
    await callback.answer(status_message)
