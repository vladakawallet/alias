from bot_setup import bot, rediscli, logger, timer_manager, mysqlcli, mysql_pool
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
import asyncio
from utils.languages import LANGUAGES
from redis import RedisError
import aiomysql
import random
import utils.keyboards as keyboards
from aiogram.exceptions import TelegramRetryAfter


async def correct(message: Message, state: FSMContext):
    try:
        team = await state.get_data()
        timer = await rediscli.get_session_field(team["group_id"], "timer_state")
        guessed, missed, score = team["guessed"], team["missed"], team["score"]
        if len(team["words"]) < 3:
            offset = await rediscli.get_session_field(team["group_id"], "offset")
            new_words = (await mysqlcli.get_words(mysql_pool, int(offset), 100)) + team["words"]
            await rediscli.update_session_data(team["group_id"], {"words": new_words, "offset": int(offset)+100})
            team["words"] = new_words
        words = team["words"]
        if timer != "done":
            word = words.pop(random.randint(0, len(words)-1))
            score += 1
            guessed += 1
            await state.update_data(guessed=guessed, words=words, score=score, missed=missed)
            await message.answer(text=f"{word}")
            await bot.edit_message_text(f"**Раунд команди {team["team"]}**\nВгадано: {guessed}, пропущено: {missed}", 
                team["group_id"], 
                team["result_message"], 
                parse_mode=ParseMode.MARKDOWN)
        else:
            session_data = await rediscli.redis_get_pipeline(team["group_id"], ["timer_state", "words", "win_score", "turn", "teams_message", "teams", "timer_message"])
            await bot.delete_message(chat_id=team["group_id"], message_id=session_data["timer_message"])
            score += 1
            if score >= int(session_data["win_score"]):
                await bot.delete_message(chat_id=team["group_id"], message_id=session_data["teams_message"])
                await bot.edit_message_text(text=f"Раунд завершено. Перемогла команда {team["team"]}! Кількість очок: {score}",
                                        chat_id=team["group_id"], message_id=team["result_message"])
                await message.answer("Вітаю, твоя команда перемогла!", reply_markup=ReplyKeyboardRemove())
                await bot.send_message(text="Вітаю, твоя команда перемогла!", chat_id=session_data["teams"][team["team"]]["members"][1][1])
                await state.clear()
                data = {"result_message": "", "main_state": "", "teams_message": "", "turn": 0, "teams": {}, "start_message": "", "string": "", "timer_state": "", "timer_message": "", "words": []}
                await rediscli.redis_set_pipeline(chat_id=team["group_id"], data=data)
                logger.info(f"game ended on {team['group_id']}")
                return
            await message.answer(text="Раунд завершено, чекай наступної черги.", reply_markup=ReplyKeyboardRemove())
            await bot.edit_message_text(chat_id=team["group_id"], message_id=team["result_message"],
                                        text=f"Раунд команди {team["team"]} завершено з кількістю в {score} балів!")
            index = int(session_data["turn"])
            tm = list(session_data["teams"].keys())[index]
            curTeam = session_data["teams"][tm]["members"]
            await bot.delete_message(chat_id=team["group_id"], message_id=session_data["teams_message"])
            msg = await bot.send_message(chat_id=team["group_id"],
                            text=f"Наступна команда <b>{tm}</b>.\n<a href=\"tg://user?id={curTeam[0][1]}\">{curTeam[0][0]}</a> відгадує, <a href=\"tg://user?id={curTeam[1][1]}\">{curTeam[1][0]}</a> пояснює", parse_mode=ParseMode.HTML)
            session_data["teams_message"] = msg.message_id
            await bot.send_message(chat_id=curTeam[1][1], text="Тисни *почати*🚀", 
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Почати!", callback_data=f"prvtGame: {tm} {team["group_id"]}")]]),
                            parse_mode=ParseMode.MARKDOWN)
            curTeam[0], curTeam[1] = curTeam[1], curTeam[0]
            await state.clear()
            # await create_timer_task(team["group_id"], 20, "game")
            await timer_manager.create_timer_task(team["group_id"], 20, "game")
            session_data["teams"][team["team"]]["score"] = score
            session_data["teams"][tm]["members"] = curTeam
            session_data["main_state"] = "game"
            session_data["words"] = team["words"]
            await rediscli.redis_set_pipeline(team["group_id"], session_data)
    except RedisError as e:
        logger.error(f"redis error in {team["group_id"]} on correct answer: {e}")
        await bot.send_message(team["group_id"], LANGUAGES['en']['database_error'])
        await message.answer(text=LANGUAGES['en']['database_error'], reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await timer_manager.cancel_timer_task(team["group_id"])
    except aiomysql.Error as e:
        logger.error(f"mysql error in {team["group_id"]} on incorrect answer: {e}")
        await bot.send_message(team["group_id"], LANGUAGES['en']['database_error'])
        await message.answer(text=LANGUAGES['en']['database_error'], reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await timer_manager.cancel_timer_task(team["group_id"])
    except TelegramRetryAfter as e:
        logger.error(f"countinious requests are noticed in {team["group_id"]}: {e}")
        await message.answer(f"too many answers per second, you are probably cheating. slow down, please! next answer is possible in {e.retry_after} seconds", reply_markup=ReplyKeyboardRemove())
        await asyncio.sleep(e.retry_after)
        await message.answer(f"go on!", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅")], [KeyboardButton(text="Пропуск❌")]], resize_keyboard=True))
    except Exception as e:
        logger.error(f"an error in {team["group_id"]} on incorrect answer: {e}")
        await bot.send_message(team["group_id"], LANGUAGES['en']['general_error'])
        await message.answer(text=LANGUAGES['en']['general_error'], reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await timer_manager.cancel_timer_task(team["group_id"])
        try: 
            data = {"main_state": "", "teams_message": "", "turn": 0, "teams": {}, "result_message": "", "start_message": "", "string": "", "timer_state": "", "timer_message": "", "words": []}
            await rediscli.redis_set_pipeline(team["group_id"], data)
        except RedisError as e:
            logger.error(f"redis error in {team["group_id"]} on incorrect answer: {e}")

async def incorrect(message: Message, state: FSMContext):
    try:
        team = await state.get_data()
        timer = await rediscli.get_session_field(team["group_id"], "timer_state")
        guessed, missed, score = team["guessed"], team["missed"], team["score"]
        if len(team["words"]) < 3:
            offset = await rediscli.get_session_field(team["group_id"], "offset")
            new_words = (await mysqlcli.get_words(mysql_pool, int(offset), 100)) + team["words"]
            await rediscli.update_session_data(team["group_id"], {"words": new_words, "offset": int(offset)+100})
            team["words"] = new_words
        words = team["words"]
        if timer != "done":
            word = words.pop(random.randint(0, len(words)-1))
            score -= 1
            missed += 1
            await state.update_data(guessed=guessed, words=words, score=score, missed=missed)
            await message.answer(text=f"{word}")
            await bot.edit_message_text(f"**Раунд команди {team["team"]}**\nВгадано: {guessed}, пропущено: {missed}", team["group_id"], team["result_message"], parse_mode=ParseMode.MARKDOWN)
        else:
            session_data = await rediscli.redis_get_pipeline(team["group_id"], ["timer_state", "words", "win_score", "turn", "teams_message", "teams", "timer_message"])
            await bot.delete_message(chat_id=team["group_id"], message_id=session_data["timer_message"])
            score -= 1
            if score >= int(session_data["win_score"]):
                await bot.delete_message(chat_id=team["group_id"], message_id=session_data["teams_message"])
                await bot.edit_message_text(text=f"Раунд завершено. Перемогла команда {team["team"]}! Кількість очок: {score}",
                                        chat_id=team["group_id"], message_id=team["result_message"])
                await message.answer("Вітаю, твоя команда перемогла!", reply_markup=ReplyKeyboardRemove())
                await bot.send_message(text="Вітаю, твоя команда перемогла!", chat_id=session_data["teams"][team["team"]]["members"][1][1])
                await state.clear()
                data = {"main_state": "", "teams_message": "", "turn": 0, "teams": {}, "start_message": "", "string": "", "timer_state": "", "timer_message": "", "words": []}
                await rediscli.redis_set_pipeline(chat_id=team["group_id"], data=data)
                logger.info(f"game ended on {team['group_id']}")
                return
            await message.answer(text="Раунд завершено, чекай наступної черги.", reply_markup=ReplyKeyboardRemove())
            await bot.edit_message_text(chat_id=team["group_id"], message_id=team["result_message"],
                                        text=f"Раунд команди {team["team"]} завершено з кількістю в {score} балів!")
            index = int(session_data["turn"])
            tm = list(session_data["teams"].keys())[index]
            curTeam = session_data["teams"][tm]["members"]
            await bot.delete_message(chat_id=team["group_id"], message_id=session_data["teams_message"])
            msg = await bot.send_message(chat_id=team["group_id"],
                            text=f"Наступна команда <b>{tm}</b>.\n<a href=\"tg://user?id={curTeam[0][1]}\">{curTeam[0][0]}</a> відгадує, <a href=\"tg://user?id={curTeam[1][1]}\">{curTeam[1][0]}</a> пояснює", parse_mode=ParseMode.HTML)
            session_data["teams_message"] = msg.message_id
            await bot.send_message(chat_id=curTeam[1][1], text="Тисни *почати*🚀", 
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Почати!", callback_data=f"prvtGame: {tm} {team["group_id"]}")]]),
                            parse_mode=ParseMode.MARKDOWN)
            curTeam[0], curTeam[1] = curTeam[1], curTeam[0]
            await state.clear()
            await timer_manager.recreate_timer_task(team["group_id"], 20, "game")
            session_data["teams"][tm]["members"] = curTeam
            session_data["teams"][team["team"]]["score"] = score
            session_data["main_state"] = "game"
            session_data["words"] = team["words"]
            await rediscli.redis_set_pipeline(team["group_id"], session_data)
    except RedisError as e:
        logger.error(f"redis error in {team["group_id"]} on incorrect answer: {e}")
        await bot.send_message(team["group_id"], LANGUAGES['en']['database_error'])
        await message.answer(text=LANGUAGES['en']['database_error'], reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await timer_manager.cancel_timer_task(team["group_id"])
    except aiomysql.Error as e:
        logger.error(f"mysql error in {team["group_id"]} on incorrect answer: {e}")
        await bot.send_message(team["group_id"], LANGUAGES['en']['database_error'])
        await message.answer(text=LANGUAGES['en']['database_error'], reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await timer_manager.cancel_timer_task(team["group_id"])
    except TelegramRetryAfter as e:
        logger.error(f"countinious requests are noticed in {team["group_id"]}: {e}")
        await message.answer(f"too many answers per second, you are probably cheating. slow down, please! next answer is possible in {e.retry_after} seconds", reply_markup=ReplyKeyboardRemove())
        await asyncio.sleep(e.retry_after)
        await message.answer(f"go on!", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅")], [KeyboardButton(text="Пропуск❌")]], resize_keyboard=True))
    except Exception as e:
        logger.error(f"an error in {team["group_id"]} on incorrect answer: {e}")
        await bot.send_message(team["group_id"], LANGUAGES['en']['general_error'])
        await message.answer(text=LANGUAGES['en']['general_error'], reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await timer_manager.cancel_timer_task(team["group_id"])
        try: 
            data = {"main_state": "", "teams_message": "", "turn": 0, "teams": {}, "result_message": "", "start_message": "", "string": "", "timer_state": "", "timer_message": "", "words": []}
            await rediscli.redis_set_pipeline(team["group_id"], data)
        except RedisError as e:
            logger.error(f"redis error in {team["group_id"]} on incorrect answer: {e}")
