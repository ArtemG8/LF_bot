import random
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from lexicon import LEXICON_RU, MOTIVATIONAL_MESSAGES
from database import (
    get_or_create_user,
    add_flow_record,
    add_sprint_record,
    get_user_productivity_history,
    get_productivity_sum_by_day,
    get_productivity_sum_for_month,
    get_all_months_with_data,
    get_total_productivity,
)
from keyboards import create_cancel_keyboard, create_flow_active_kb, create_flow_paused_kb, create_history_inline_kb
from states import RecordStates

router = Router()

# Обработчик команды /start
@router.message(CommandStart())
async def process_start_command(message: Message, session: AsyncSession, state: FSMContext):
    await state.clear() # Очищаем состояние, если пользователь перезапускает бота
    user_data = message.from_user
    user = await get_or_create_user(
        session,
        telegram_id=user_data.id,
        username=user_data.username
    )
    if user.created_at == user.created_at: # Простая проверка на нового/вернувшегося пользователя
        await message.answer(LEXICON_RU['/start'])
    else:
        await message.answer(LEXICON_RU['welcome_back'])

# Обработчик команды /help
@router.message(Command(commands='/start'))
async def process_help_command(message: Message):
    await message.answer(LEXICON_RU['/start'])


