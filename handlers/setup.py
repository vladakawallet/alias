from bot_setup import bot, rediscli, logger, timer_manager
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.enums.parse_mode import ParseMode
from utils.languages import LANGUAGES
import base64
from redis import RedisError
from handlers.utils import check_bot_admin
import utils.keyboards as keyboards

async def accept_invite_query(chat_id, first_name, user_id):
    try:
        await rediscli.add_session_player(chat_id, [first_name, user_id])
        session_data = await rediscli.redis_get_pipeline(chat_id, ["players", "start_message"])
        players_string = ', '.join([f"<a href=\"tg://user?id={id}\">{name}</a>" for name, id in session_data["players"]])
        # if len(session_data["players"]) == 4:#CORRECT
        #     await bot.edit_message_text(chat_id=chat_id, text=f"<b>Максимальна к-ть гравців зареєстрована, починайте гру!</b>\n\n<b>Учасники</b>\n{players_string}\nВсього гравців: {len(session_data["players"])}",
        #                                  message_id=session_data["start_message"],
        # reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Визначити команди🎮", callback_data="teamsState")]]))
        info = await bot.get_me()
        data = f"from_group|{chat_id}"
        encoded_data = base64.b64encode(data.encode('utf-8')).decode('utf-8')
        deep_link = f"https://t.me/{info.username}?start={encoded_data}"
        invite_alias_link_btn = [[InlineKeyboardButton(text="Приєднатися", url=deep_link)],  [InlineKeyboardButton(text="Визначити команди🎮", callback_data="teamsState")]]
        await bot.edit_message_text(chat_id=chat_id, message_id=session_data["start_message"],
        text=f'<b>Приєднатися до гри</b>\n\n<b>Учасники</b>\n{players_string}\nВсього гравців: {len(session_data["players"])}',
        parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=invite_alias_link_btn))
        logger.info(f"{user_id} invite query accepted")
    except RedisError as e:
        logger.error(f"redis failed to accept invite query in {chat_id}: {e}")
        await bot.send_message(chat_id, LANGUAGES['en']['database_error'])
    except Exception as e:
        logger.error(f"an error on accepting invite query in {chat_id}: {e}")
        await bot.send_message(chat_id, LANGUAGES['en']['general_error'])
        try: 
            data = {"main_state": "", "start_message": "", "players": "", "timer_task": ""}
            await rediscli.update_session_data(chat_id, data)
        except RedisError as e:
            logger.error(f"redis failed to accept invite query in {chat_id}: {e}")


async def game_command(message: Message):
    try:
        if message.chat.type == 'private': 
            await bot.delete_message(message.chat.id, message.message_id)
            await bot.send_message(message.chat.id, "Команда доступна лише у гпуповому чаті!", reply_markup=keyboards.start_inline_kb)
            return
        if await check_bot_admin(message.chat.id):
            main_state = await rediscli.get_session_field(message.chat.id, "main_state")
            if main_state in ["teams", "setup", "game", "players"] or main_state.startswith("prvtgame"):
                await bot.delete_message(message.chat.id, message.message_id)
            else:
                await rediscli.update_session_field(message.chat.id, "main_state", "setup")
                info = await bot.get_me()
                data = f"from_group|{int(message.chat.id)}"
                encoded_data = base64.b64encode(data.encode('utf-8')).decode('utf-8')
                deep_link = f"https://t.me/{info.username}?start={encoded_data}"
                invite_alias_link_btn = [[InlineKeyboardButton(text="Приєднатися", url=deep_link)],  [InlineKeyboardButton(text="Визначити команди🎮", callback_data="teamsState")]]
                msg = await message.answer(text="*Приєднатися до гри*", parse_mode=ParseMode.MARKDOWN, 
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=invite_alias_link_btn))
                await rediscli.update_session_field(message.chat.id, "start_message", msg.message_id)
                await timer_manager.create_timer_task(message.chat.id, 90, "setup")
                logger.info(f"new game is created on {message.chat.id}")
        else:
            await message.answer(LANGUAGES['uk']['bot_is_still_member'], parse_mode=ParseMode.MARKDOWN)
            await bot.delete_message(message.chat.id, message.message_id)
    except RedisError as e:
        logger.error(f"redis failed to create a new game in {message.chat.id}: {e}")
        await bot.send_message(message.chat.id, LANGUAGES['en']['database_error'])
        await timer_manager.cancel_timer_task(message.chat.id)
    except Exception as e:
        logger.error(f"an error on creating a new game in {message.chat.id}: {e}")
        await bot.send_message(message.chat.id, LANGUAGES['en']['general_error'])
        await timer_manager.cancel_timer_task(message.chat.id)
        try: 
            data = {"main_state": "", "start_message": "", "players": "", "timer_task": ""}
            await rediscli.update_session_data(message.chat.id, data)
        except RedisError as e:
            logger.error(f"redis failed to create a new game in {message.chat.id}: {e}")


async def cancel_command(message: Message):
    try:
        if message.chat.type == "group" or message.chat.type == "supergroup":
            state = await rediscli.get_session_field(message.chat.id, "main_state")
            if state.startswith("prvtgame") or state == "game":
                await bot.delete_message(message.chat.id, message.message_id)
            else:
                message_id = await rediscli.get_session_field(message.chat.id, "start_message")
                await timer_manager.cancel_timer_task(message.chat.id)
                await bot.delete_message(message.chat.id, message.message_id)
                if state == "setup":
                    data = {"main_state": "", "start_message": "", "players": "", "timer_task": ""}
                    await rediscli.update_session_data(message.chat.id, data)
                    await bot.edit_message_text(chat_id=message.chat.id, text="Реєстрацію скасовано", message_id=message_id)
                    logger.info(f"registration is cancelled on {message.chat.id}")
                elif state == "teams":
                    data = {"teams_message": "", "string": "", "main_state": "", "start_message": "", "teams": {}, "players": [], "timer_task": ""}                
                    await rediscli.redis_set_pipeline(message.chat.id, data)
                    await bot.edit_message_text("Реєстрацію скасовано", message.chat.id, message_id)
                    logger.info(f"registration is cancelled on {message.chat.id}")
                elif state == "players":
                    teams_message_id = await rediscli.get_session_field(message.chat.id, "teams_message")
                    await bot.delete_message(message.chat.id, teams_message_id)
                    await bot.edit_message_text("Реєстрацію скасовано", message.chat.id, message_id)
                    data = {"teams_message": "", "string": "", "main_state": "", "start_message": "", "teams": {}, "players": [], "timer_task": ""}                
                    await rediscli.redis_set_pipeline(message.chat.id, data)
                    logger.info(f"registration is cancelled on {message.chat.id}")
                else:
                    await message.answer("Наразі я не бачу активної реєстрації у вашій групі.")
        else:
            await message.answer("Команда працює лише у груповому чаті!")
            await bot.delete_message(message.chat.id, message.message_id)
    except RedisError as e:
        logger.error(f"redis failed to cancel a registration in {message.chat.id}: {e}")
        await bot.send_message(message.chat.id, LANGUAGES['en']['database_error'])
        await timer_manager.cancel_timer_task(message.chat.id)
    except Exception as e:
        logger.error(f"an error on cancelling a registration in {message.chat.id}: {e}")
        await bot.send_message(message.chat.id, LANGUAGES['en']['general_error'])
        await timer_manager.cancel_timer_task(message.chat.id)
        try: 
            data = {"main_state": "", "teams_message": "", "turn": 0, "teams": {}, "result_message": "", "start_message": "", "string": "", "timer_state": "", "timer_message": "", "words": []}
            await rediscli.redis_set_pipeline(message.chat.id, data)
        except RedisError as e:
            logger.error(f"redis failed to cancel a registration in {message.chat.id}: {e}")