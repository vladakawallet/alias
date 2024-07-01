from bot_setup import bot, rediscli, logger
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
import utils.keyboards as keyboards
from handlers.utils import Settings, check_bot_admin
from utils.languages import LANGUAGES
from redis import RedisError


async def settings_command(message: Message, state: FSMContext):
    try:  
        if message.chat.type == "private":
            await message.answer("Команда працює лише у груповому чаті!")
            await bot.delete_message(message.chat.id, message.message_id)
        elif message.chat.type == "group" or message.chat.type == "supergroup":
            main_state = await rediscli.get_session_field(message.chat.id, "main_state")
            if main_state in ["teams", "players", "setup", "game"] or main_state.startswith("prvtgame"):
                await bot.delete_message(message.chat.id, message.message_id)
                return
            if await check_bot_admin(message.chat.id) == False:
                await message.answer(LANGUAGES['uk']['bot_is_still_member'])
                await bot.delete_message(message.chat.id, message.message_id)
                return
            msg = await message.answer(f"<a href=\"tg://user?id={message.from_user.id}\">{message.from_user.first_name}</a>, Вибери опцію для налаштування:", reply_markup=keyboards.settings_inline_kb, parse_mode=ParseMode.HTML)
            await state.set_state(Settings.menu)
            await state.update_data(msg_id=msg.message_id)
            logger.info(f"settings state is entered on {message.chat.id}")
    except RedisError as e:
        logger.error(f"redis error in {message.chat.id} on settings command: {e}")
        await message.answer(LANGUAGES['en']['database_error'])
        await state.clear()
    except Exception as e:
        logger.error(f"an error in {message.chat.id} on settings command: {e}")
        await message.answer(LANGUAGES['en']['general_error'])
        await state.clear()

#winscore
async def winscore_callback(callback: CallbackQuery, state: FSMContext):
    try:
        msgid = await state.get_data()
        await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=msgid["msg_id"], text=f"<a href=\"tg://user?id={callback.from_user.id}\">{callback.from_user.first_name}</a>, введи нове значення для переможних очків (мін.5, мах. 25)", parse_mode=ParseMode.HTML)
        await state.set_state(Settings.winscore)
    except Exception as e:
        logger.error(f"an error in {callback.message.chat.id} on settings.winscore: {e}")
        await callback.message.answer(LANGUAGES['en']['general_error'])
        await state.clear()


async def new_winscore(message: Message, state: FSMContext):
    try: 
        await bot.delete_message(message.chat.id, message.message_id)
        msgid = await state.get_data()
        if int(message.text) >= 5 and int(message.text) <= 25:
            await bot.edit_message_text(chat_id=message.chat.id, message_id=msgid["msg_id"], text=f"Нове значення переможних очків встановлено: *{message.text}*", parse_mode=ParseMode.MARKDOWN)
            await rediscli.update_session_field(message.chat.id, "win_score", int(message.text))
            msg = await message.answer(f"<a href=\"tg://user?id={message.from_user.id}\">{message.from_user.first_name}</a>,Вибери опцію для налаштування:", reply_markup=keyboards.settings_inline_kb, parse_mode=ParseMode.HTML)
            await state.update_data(msg_id=msg.message_id)
            await state.set_state(Settings.menu)
            logger.info(f"winscore is changed to {message.text} on {message.chat.id}")
        else: 
            await bot.edit_message_text(chat_id=message.chat.id, message_id=msgid["msg_id"], text="Невірне значення! Введи число від 5 до 25!")
    except ValueError as e:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=msgid["msg_id"], text="Невірне значення! Введи число від 10 до 25!")
    except RedisError as e:
        logger.error(f"redis unable to set a new winscore in {message.chat.id}: {e}")
        await message.answer(LANGUAGES['en']['database_error'])
        await state.clear()
    except Exception as e:
        logger.error(f"an error in {message.chat.id} on newwinscore: {e}")
        await message.answer(LANGUAGES['en']['general_error'])
        await state.clear()

#roundtimer
async def roundtimer_callback(callback: CallbackQuery, state: FSMContext):
    try:
        msgid = await state.get_data()
        await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=msgid["msg_id"], text=f"<a href=\"tg://user?id={callback.from_user.id}\">{callback.from_user.first_name}</a>, введи нове значення для таймера раунду (мін.30, мах. 120)", parse_mode=ParseMode.HTML)
        await state.set_state(Settings.roundtimer)
    except Exception as e:
        logger.error(f"an error in {callback.message.chat.id} on settings.roundtimer: {e}")
        await callback.message.answer(LANGUAGES['en']['general_error'])
        await state.clear()

async def new_roundtimer(message: Message, state: FSMContext):
    try: 
        await bot.delete_message(message.chat.id, message.message_id)
        msgid = await state.get_data()
        if int(message.text): 
            if int(message.text) >= 30 and int(message.text) <= 120:
                await bot.edit_message_text(chat_id=message.chat.id, message_id=msgid["msg_id"],text=f"Нове значення переможних таймера раунду: *{message.text}*", parse_mode=ParseMode.MARKDOWN)
                await rediscli.update_session_field(message.chat.id, "timer", message.text)
                msg = await message.answer(f"<a href=\"tg://user?id={message.from_user.id}\">{message.from_user.first_name}</a>,Вибери опцію для налаштування:", reply_markup=keyboards.settings_inline_kb, parse_mode=ParseMode.HTML)
                await state.set_state(Settings.menu)
                await state.update_data(msg_id=msg.message_id)
                logger.info(f"roundtimer is changed to {message.text} on {message.chat.id}")
            else: 
                await message.answer(chat_id=message.chat.id, message_id=msgid["msg_id"], text="Невірне значення! Введи число від 30 до 120!")
    except ValueError as e:
        await message.answer(chat_id=message.chat.id, message_id=msgid["msg_id"], text="Невірне значення! Введи число від 30 до 120")
    except RedisError as e:
        logger.error(f"redis unable to set a new roundtimer in {message.chat.id}: {e}")
        await message.answer(LANGUAGES['en']['database_error'])
        await state.clear()
    except Exception as e:
        logger.error(f"an error in {message.chat.id} on new_roundtimer: {e}")
        await message.answer(LANGUAGES['en']['general_error'])
        await state.clear()


async def cancel_settings(callback: CallbackQuery, state: FSMContext):
    try:
        msgid = await state.get_data()
        await bot.edit_message_text(text="Вихід з режиму налаштувань!", chat_id=callback.message.chat.id, message_id=msgid["msg_id"])
        await state.clear()
        logger.info(f"settings state is exited on {callback.message.chat.id}")
    except Exception as e:
        logger.error(f"an error in {callback.message.chat.id} on settings.cancel: {e}")
        await callback.message.answer(LANGUAGES['en']['general_error'])
        await state.clear()