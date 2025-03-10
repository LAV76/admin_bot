from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.admin.menu import get_back_to_menu_keyboard

router = Router()

# Обработчик create_post удален, так как он полностью реализован в handlers/admin/create_post.py

@router.callback_query(F.data == "delete_post")
async def delete_post(callback: CallbackQuery):
    """Обработчик удаления поста"""
    await callback.message.delete()
    await callback.message.answer(
        'Потом тут можно будет удалить пост',
        reply_markup=get_back_to_menu_keyboard()
    ) 