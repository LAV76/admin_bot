from aiogram.fsm.state import State, StatesGroup

class RoleStates(StatesGroup):
    """Состояния для управления ролями"""
    waiting_for_user_id_add = State()
    waiting_for_role_add = State()
    waiting_for_user_id_remove = State()
    waiting_for_role_remove = State()
    confirm_action = State() 