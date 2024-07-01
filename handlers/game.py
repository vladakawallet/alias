from bot_setup import bot, rediscli, logger, timer_manager, mysqlcli
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from handlers.utils import Game
from utils.languages import LANGUAGES
from redis import RedisError
import aiomysql
import random

async def start_game_callback(callback: CallbackQuery):
    global mysql_pool
    try:
        await rediscli.update_session_field(callback.message.chat.id, "main_state", "game")
        session_data = await rediscli.redis_get_pipeline(callback.message.chat.id, ["turn", "teams", "teams_message", "offset", "words"])
        index = int(session_data["turn"])
        tm = list(session_data["teams"].keys())[index]
        curTeam = session_data["teams"][tm]["members"]
        await callback.answer("Починаємо!")
        await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=session_data["teams_message"], 
                            text=f"Розпочинає команда <b>{tm}</b>.\n<a href=\"tg://user?id={curTeam[0][1]}\">{curTeam[0][0]}</a> відгадує, <a href=\"tg://user?id={curTeam[1][1]}\">{curTeam[1][0]}</a> пояснює", 
                            parse_mode=ParseMode.HTML)
        await bot.send_message(chat_id=curTeam[1][1], text="Тисни кнопку почати, і ти отримаєш перше слово!",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Почати!", callback_data=f"prvtGame: {tm} {callback.message.chat.id}")]]))
        curTeam[0], curTeam[1] = curTeam[1], curTeam[0]
        session_data["teams"][tm]["members"] = curTeam
        if mysql_pool is None:
            mysql_pool = await mysqlcli.mysql_connection_pool()
        offset = await rediscli.get_session_field(callback.message.chat.id, "offset")
        words = await mysqlcli.get_words(mysql_pool, int(offset), 100)
        session_data["offset"] = int(offset)+100
        session_data["words"] = words
        await rediscli.redis_set_pipeline(callback.message.chat.id, session_data)
        await timer_manager.recreate_timer_task(callback.message.chat.id, 20, "game")
        logger.info(f"game state on {callback.message.chat.id}")
    except RedisError as e:
        logger.error(f"redis error in {callback.message.chat.id} on game state: {e}")
        await bot.send_message(callback.message.chat.id, LANGUAGES['en']['database_error'])
        await timer_manager.cancel_timer_task(callback.message.chat.id)
    except aiomysql.Error as e:
        logger.error(f"mysql error in {callback.message.chat.id} on game state: {e}")
        await bot.send_message(callback.message.chat.id, LANGUAGES['en']['database_error'])
        await timer_manager.cancel_timer_task(callback.message.chat.id)
    except Exception as e:
        logger.error(f"an error in {callback.message.chat.id} on game state: {e}")
        await bot.send_message(callback.message.chat.id, LANGUAGES['en']['general_error'])
        await timer_manager.cancel_timer_task(callback.message.chat.id)
        try: 
            data = {"main_state": "", "teams_message": "", "turn": 0, "teams": {}, "start_message": "", "string": "", "players": [], "timer_task": ""}
            await rediscli.redis_set_pipeline(callback.message.chat.id, data)
        except RedisError as e:
             logger.error(f"redis error in {callback.message.chat.id} on game state: {e}")

async def start_privategame_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Гру почато!")
    data = callback.data.split()
    try:
        session_data = await rediscli.redis_get_pipeline(data[2], ["teams", "timer", "words", "turn"])
        index = int(session_data["turn"])
        if index >= len(session_data["teams"].keys()):
            index = 0
        else:
            index += 1
        msg = await bot.send_message(data[2], f"**Раунд команди {data[1]}**\nВгадано: 0, пропущено: 0", parse_mode=ParseMode.MARKDOWN)
        await rediscli.update_session_data(data[2], {"turn": index, "main_state": f"prvtgame {callback.message.chat.id}", "timer_state": "running", "result_message": msg.message_id})
        words = session_data["words"]
        score = int(session_data["teams"][data[1]]["score"])
        word = words.pop(random.randint(0, len(words)-1))
        await state.set_state(Game.processing)
        await state.update_data(team=data[1], guessed=0, missed=0, group_id=data[2], words=words, score=score, result_message=msg.message_id)
        await bot.send_message(chat_id=callback.message.chat.id, text=f"{word}",
                            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅")], [KeyboardButton(text="Пропуск❌")]], resize_keyboard=True))
        await timer_manager.recreate_timer_task(data[2], int(session_data["timer"]), f"prvtgame {callback.message.chat.id}", callback.message.chat.id)
        logger.info(f"game started on {data[2]}")
    except RedisError as e:
        logger.error(f"redis error in {callback.message.chat.id} on privategame state: {e}")
        await bot.send_message(data[2], LANGUAGES['en']['database_error'])
        await callback.message.answer(LANGUAGES['en']['database_error'])
        await state.clear()
        await timer_manager.cancel_timer_task(data[2])
    except ValueError as e:
        logger.error(f"redis value error in {callback.message.chat.id} on privategame state: {e}")
        await bot.send_message(data[2], LANGUAGES['en']['database_error'])
        await callback.message.answer(LANGUAGES['en']['database_error'])
        await state.clear()
        await timer_manager.cancel_timer_task(data[2])
    except Exception as e:
        logger.error(f"an error in {callback.message.chat.id} on privategame state: {e}")
        await bot.send_message(data[2], LANGUAGES['en']['general_error'])
        await callback.message.answer(LANGUAGES['en']['general_error'])
        await state.clear()
        await timer_manager.cancel_timer_task(data[2])
        try: 
            update_data = {"main_state": "", "teams_message": "", "turn": 0, "teams": {}, "start_message": "", "string": "", "timer_state": "", "timer_message": ""}
            await rediscli.redis_set_pipeline(data[2], update_data)
        except RedisError as e:
            logger.error(f"redis error in {callback.message.chat.id} on privategame state: {e}")