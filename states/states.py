from aiogram.fsm.state import StatesGroup, State


class PickTeamStates(StatesGroup):
    choosing_position = State()
    choosing_player = State()
    removing_player = State()


class AdminStates(StatesGroup):
    waiting_for_password = State()
    admin_menu = State()
    changing_password = State()
    adding_match_opponent = State()
    adding_match_datetime = State()
    selecting_match_to_score = State()
    entering_player_points = State()
