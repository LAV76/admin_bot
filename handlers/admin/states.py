from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    """Состояния для админ-панели"""
    waiting_for_user_id = State()
    confirm_role = State()
    waiting_for_notes = State()

class ContentManagerStates(StatesGroup):
    """Состояния для контент-менеджера"""
    waiting_for_user_id = State()
    confirm_role = State()
    waiting_for_notes = State()

class RemoveRoleStates(StatesGroup):
    """Состояния для удаления роли"""
    waiting_for_user_id = State()
    select_role = State()
    confirm_remove = State()
    waiting_for_notes = State()
    confirm_action = State()

class RoleStates(StatesGroup):
    """Состояния для управления ролями"""
    waiting_for_user_id_add = State()
    waiting_for_role_add = State()
    waiting_for_user_id_remove = State()
    waiting_for_role_remove = State()
    confirm_action = State() 