# Обработчик ответа на добавление канала
@router.callback_query(F.data.startswith("add_channel:"))
@role_required("admin")
async def add_channel_callback(callback: CallbackQuery, bot: Bot):
    """Обрабатывает callback-запрос для добавления канала"""
    try:
        # Получаем chat_id из callback данных
        chat_id = int(callback.data.split(":")[1])
        user_id = callback.from_user.id
        
        logger.info(f"Пользователь {user_id} пытается добавить канал с ID {chat_id}")
        
        # Проверяем доступ бота к каналу
        channel_service = ChannelService()
        bot_access = await channel_service.check_bot_access(chat_id, bot)
        
        if not bot_access.get("success", False):
            error_msg = bot_access.get("message", "Неизвестная ошибка")
            logger.error(f"Ошибка доступа к каналу {chat_id}: {error_msg}")
            await callback.message.edit_text(
                f"❌ Ошибка доступа к каналу:\n{error_msg}\n\nУбедитесь, что бот добавлен в канал и имеет необходимые права.",
                reply_markup=get_channel_management_keyboard()
            )
            await callback.answer()
            return
        
        # Получаем данные о канале
        title = bot_access.get("title", f"Канал {chat_id}")
        username = bot_access.get("username")
        channel_type = bot_access.get("type", "channel")
        
        # Добавляем канал в базу данных
        result = await channel_service.add_channel(
            chat_id=chat_id,
            title=title,
            chat_type=channel_type,
            username=username,
            added_by=user_id
        )
        
        # Проверяем результат
        if not result:
            logger.error(f"Не удалось добавить канал {chat_id}")
            await callback.message.edit_text(
                "❌ Ошибка!\n\nНе удалось добавить канал. Попробуйте еще раз.",
                reply_markup=get_channel_management_keyboard()
            )
            await callback.answer()
            return
        
        # Проверяем, был ли канал успешно добавлен или уже существует
        if result.get("success") == False:
            error_type = result.get("error")
            if error_type == "already_exists":
                # Канал уже существует
                await callback.message.edit_text(
                    f"ℹ️ Информация\n\n{result.get('message', 'Этот канал уже добавлен в базу данных.')}",
                    reply_markup=get_channel_management_keyboard()
                )
            else:
                # Другая ошибка
                await callback.message.edit_text(
                    f"❌ Ошибка!\n\n{result.get('message', 'Не удалось добавить канал. Попробуйте еще раз.')}",
                    reply_markup=get_channel_management_keyboard()
                )
        else:
            # Канал успешно добавлен
            await callback.message.edit_text(
                f"✅ Канал успешно добавлен!\n\n"
                f"Название: {title}\n"
                f"ID: {chat_id}\n"
                f"Тип: {channel_type}",
                reply_markup=get_channel_management_keyboard()
            )
        
        await callback.answer()
    except Exception as e:
        log_error(logger, "Ошибка при добавлении канала", e)
        await callback.message.edit_text(
            "❌ Произошла ошибка при добавлении канала. Пожалуйста, попробуйте еще раз.",
            reply_markup=get_channel_management_keyboard()
        )
        await callback.answer() 