from aiogram.fsm.state import StatesGroup, State


class PickTeamStates(StatesGroup):
    choosing_position = State()
    choosing_player = State()
    removing_player = State()


class AdminStates(StatesGroup):
    waiting_for_password = State()
    admin_menu = State()
    changing_password = State()

    # Match Management
    managing_matches = State()
    adding_match_opponent = State()
    adding_match_datetime = State()
    selecting_match_to_edit = State()
    editing_match_opponent = State()
    editing_match_datetime = State()

    # Player Management
    managing_players = State()
    viewing_all_players = State()
    adding_player_name = State()
    adding_player_position = State()
    selecting_player_to_edit = State()
    editing_player_name = State()
    editing_player_position = State()
    selecting_player_to_delete = State()
    confirming_player_delete = State()
    confirming_delete_all_players = State()

    # Score Management
    selecting_match_to_score = State()
    entering_player_points = State()
