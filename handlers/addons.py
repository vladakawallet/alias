from bot_setup import bot, rediscli, logger
from aiogram.types import Message
from aiogram.enums.parse_mode import ParseMode
from utils.languages import LANGUAGES
from redis import RedisError



async def rules_command(message: Message):
    try:
        if message.chat.type == "group" or message.chat.type == "supergroup":
            main_state = await rediscli.get_session_field(message.chat.id, "main_state")
            if main_state in ["teams", "players", "setup", "game"] or main_state.startswith("prvtgame"):
                await bot.delete_message(message.chat.id, message.message_id)
            else: 
                await message.answer(LANGUAGES['uk']['rules'], parse_mode=ParseMode.MARKDOWN)
        elif message.chat.type == "private":
            await message.answer(LANGUAGES['uk']['rules'], parse_mode=ParseMode.MARKDOWN)
    except RedisError as e:
        logger.error(f"redis error in {message.chat.id} on /rules: {e}")
        await bot.send_message(message.chat.id, LANGUAGES['en']['database_error'])
    except Exception as e:
        logger.error(f"an error in {message.chat.id} on /rules: {e}")
        await bot.send_message(message.chat.id, LANGUAGES['en']['general_error'])
        try: 
            data = {"main_state": "", "teams_message": "", "turn": 0, "teams": {}, "result_message": "", "start_message": "", "string": "", "timer_state": "", "timer_message": "", "words": []}
            await rediscli.redis_set_pipeline(message.chat.id, data)
        except RedisError as e:
            logger.error(f"redis error in {message.chat.id} on /rules: {e}")


async def info_command(message: Message):
    try:
        if message.chat.type == "group" or message.chat.type == "supergroup":
            main_state = await rediscli.get_session_field(message.chat.id, "main_state")
            if main_state in ["teams", "players", "setup", "game"] or main_state.startswith("prvtgame"):
                await bot.delete_message(message.chat.id, message.message_id)
            else: 
                await message.answer(LANGUAGES['uk']['info'], parse_mode=ParseMode.MARKDOWN)  
        elif message.chat.type == "private":
            await message.answer(LANGUAGES['uk']['info'], parse_mode=ParseMode.MARKDOWN)
    except RedisError as e:
        logger.error(f"redis error in {message.chat.id} on /info: {e}")
    except Exception as e:
        logger.info(f"an error in {message.chat.id} on /info: {e}")