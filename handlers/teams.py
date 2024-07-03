from bot_setup import bot, logger, rediscli, timer_manager
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.enums.parse_mode import ParseMode
from handlers.utils import GameSetup
from utils.languages import LANGUAGES
from redis import RedisError

async def teams_mode(callback: CallbackQuery, state: FSMContext):
    try:
        await rediscli.update_session_field(callback.message.chat.id, "main_state", "teams")
        await timer_manager.recreate_timer_task(callback.message.chat.id, 120, "teams")
        # session_data = await rediscli.get_session_data(callback.message.chat.id)
        session_data = await rediscli.redis_get_pipeline(callback.message.chat.id, ["players", "start_message"])
        if len(session_data["players"]) % 2 != 0:
            await callback.answer("Гра почнеться лише з парною кількістю гравців")
        elif len(session_data["players"]) < 4:
            await callback.answer("Мінімальна кількість: 4")
        else:
            await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=session_data["start_message"],
            # text=f"<b>Створюємо команди</b>\n<a href=\"tg://user?id={callback.from_user.id}\">{callback.from_user.first_name}</a>, введи назву кожної команди, а потім вибери гравців", parse_mode=ParseMode.HTML)
            text=f"<b>Створюємо команди</b>", parse_mode=ParseMode.HTML)
            msg = await bot.send_message(chat_id=callback.message.chat.id, text=f"<a href=\"tg://user?id={callback.from_user.id}\">{callback.from_user.first_name}</a>, введи назву кожної команди, а потім вибери гравців",
                                   parse_mode=ParseMode.HTML)
            await callback.answer()
            await state.set_state(GameSetup.teams)
            await rediscli.update_session_field(callback.message.chat.id, "teams_message", msg.message_id)
        logger.info(f"teams state is entered on {callback.message.chat.id}")
    except RedisError as e:
        logger.error(f"redis error on teams state in {callback.message.chat.id}: {e}")
        await bot.send_message(callback.message.chat.id, LANGUAGES['en']['database_error'])
        await state.clear()
        await timer_manager.cancel_timer_task(callback.message.chat.id)
    except Exception as e:
        logger.error(f"an error on teams state in {callback.message.chat.id}: {e}")
        await bot.send_message(callback.message.chat.id, LANGUAGES['en']['general_error'])
        await state.clear()
        await timer_manager.cancel_timer_task(callback.message.chat.id)
        try: 
            data = {"teams_message": "", "string": "", "main_state": "", "start_message": "", "teams": {}, "players": [], "timer_task": ""}                
            await rediscli.redis_set_pipeline(callback.message.chat.id, data)
        except RedisError as e:
            logger.error(f"redis error on teams state in {callback.message.chat.id}: {e}")


async def team_creation(message: Message, state: FSMContext):
    try:
        # session_data = await rediscli.get_session_data(message.chat.id)
        session_data = await rediscli.redis_get_pipeline(message.chat.id, ["start_message", "teams", "players", "string", "teams_message"])
        if len(message.text) > 15:
            await bot.delete_message(message.chat.id, message.message_id)
            await bot.edit_message_text("Назва команди занадто довга (макс. 15 символів)", message.chat.id, session_data["teams_message"])
        elif message.text in session_data["teams"].keys():
            await bot.delete_message(message.chat.id, message.message_id)
            await bot.edit_message_text("Команда з такою назвою вже існує!", message.chat.id, session_data["teams_message"])
        else:
            builder = InlineKeyboardBuilder()
            if len(session_data["teams"].items()) == 0:    
                for i, id in session_data["players"]:
                    builder.button(text=f"{i}", callback_data=f"set: {id}")
                await rediscli.add_session_team(message.chat.id, message.text)
                await bot.delete_message(chat_id = message.chat.id, message_id=message.message_id)
                # await bot.edit_message_text(text="*Створи команди*", chat_id=message.chat.id, message_id=session_data["start_message"], parse_mode=ParseMode.MARKDOWN)
                # msg = await message.answer(f"Команда *{message.text}* зареєстрована, додай двох гравців⬇️", parse_mode=ParseMode.MARKDOWN, reply_markup=builder.as_markup())
                await bot.edit_message_text(chat_id=message.chat.id, message_id=session_data["teams_message"], text=f"Команда *{message.text}* зареєстрована, додай двох гравців⬇️", parse_mode=ParseMode.MARKDOWN, reply_markup=builder.as_markup())
                # await rediscli.update_session_field(message.chat.id, "teams_message", msg.message_id)
            else:
                await bot.delete_message(chat_id = message.chat.id, message_id=message.message_id) 
                result_string = session_data["string"]
                result_string += f"\nКоманда <b>{message.text}</b> зареєстрована, додай двох гравців⬇️"
                for i, id in session_data["players"]:
                    builder.button(text=f"{i}", callback_data=f"set: {id}")
                await rediscli.add_session_team(message.chat.id, message.text)
                await bot.edit_message_text(chat_id=message.chat.id, message_id=session_data["teams_message"], text=result_string, parse_mode=ParseMode.HTML,
                                        reply_markup=builder.as_markup())
            await state.set_state(GameSetup.players)
            logger.info(f"team {message.text} is created on {message.chat.id}")
    except RedisError as e:
        logger.error(f"redis failed to create a team in {message.chat.id}: {e}")
        await bot.send_message(message.chat.id, LANGUAGES['en']['database_error'])
        await state.clear()
        await timer_manager.cancel_timer_task(message.chat.id)
    except Exception as e:
        logger.error(f"an error on team adding in {message.chat.id}: {e}")
        await bot.send_message(message.chat.id, LANGUAGES['en']['general_error'])
        await state.clear()
        await timer_manager.cancel_timer_task(message.chat.id)
        try: 
            data = {"teams_message": "", "string": "", "main_state": "", "start_message": "", "teams": {}, "players": [], "timer_task": ""}                
            await rediscli.redis_set_pipeline(message.chat.id, data)
        except RedisError as e:
            logger.error(f"redis failed to create a team in {message.chat.id}: {e}")