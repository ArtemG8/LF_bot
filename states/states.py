from aiogram.fsm.state import StatesGroup, State


class PickTeamStates(StatesGroup):
    choosing_position = State()
    choosing_player = State()
    removing_player = State()


class AdminStates(StatesGroup):
    selecting_match = State()
    entering_player_points = State()
