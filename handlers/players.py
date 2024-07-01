from bot_setup import bot, rediscli, timer_manager, logger
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.enums.parse_mode import ParseMode
from handlers.utils import GameSetup
from utils.languages import LANGUAGES
from redis import RedisError

async def delete_on_players(message: Message):
    await bot.delete_message(message.chat.id, message.message_id)


async def add_user(callback: CallbackQuery, state: FSMContext):
    try:
        await rediscli.update_session_field(callback.message.chat.id, "main_state", "players")
        inner_builder = InlineKeyboardBuilder()
        userId = int(callback.data[5:])
        # session_data = await rediscli.get_session_data(callback.message.chat.id)
        session_data = await rediscli.redis_get_pipeline(callback.message.chat.id, ["players", "teams", "string", "teams_message", "start_message"])
        players = session_data["players"]
        team = list(session_data["teams"].keys())[-1]
        for index, sublist in enumerate(players):
            if userId in sublist:
                if len(session_data["teams"][team]["members"]) == 2:
                    await callback.answer("Забагато гравців для однієї команди!")
                    return
                else:
                    player = players.pop(index)
                    session_data["teams"][team]["members"].append(player)
                    results = []
                    for team_name, team_data in session_data["teams"].items():
                        members_str = ", ".join([f'<a href="tg://user?id={user[1]}">{user[0]}</a>' for user in team_data["members"]])
                        result_str = f"<b>Команда</b> {team_name}: {members_str}"
                        results.append(result_str)
                    result_string = "\n".join(results)
                    for i, id in players:
                        inner_builder.button(text=f"{i}", callback_data=f"set: {id}")
                    if len(session_data["teams"][team]["members"]) == 2:
                        session_data["string"] = result_string
                        await callback.answer() 
                        if len(session_data["players"]) != 0:
                            result_string += "\nВведи назву наступної команди, а потім вибери гравців"
                            await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=session_data["teams_message"],
                                        text=result_string, parse_mode=ParseMode.HTML, reply_markup=None)
                            await state.set_state(GameSetup.teams)
                    else:
                        await callback.answer()
                        session_data["players"] = players
                        await bot.edit_message_text(message_id=session_data["teams_message"], chat_id=callback.message.chat.id, reply_markup=inner_builder.as_markup(),
                                            text=result_string, parse_mode=ParseMode.HTML)
                    await rediscli.redis_set_pipeline(callback.message.chat.id, session_data)
                if len(session_data["players"]) == 0:
                    result_string = session_data["string"]
                    await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=session_data["start_message"], text="*Команди визначені, починаємо!*", parse_mode=ParseMode.MARKDOWN)
                    await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=session_data["teams_message"], text=result_string, parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Почати гру!", callback_data="startGame")]])),
                                                                                    # InlineKeyboardButton(text="Змінити команди", callback_data="changeGame")]]))    
                    await state.clear()
                    session_data["string"] = ""
                    await rediscli.redis_set_pipeline(callback.message.chat.id, session_data)
                    await timer_manager.recreate_timer_task(callback.message.chat.id, 30, "players")
        logger.info(f"player {userId} is added into a team in {callback.message.chat.id}")
    except RedisError as e:
        logger.error(f"redis unable to add a user in {callback.message.chat.id}: {e}")
        await bot.send_message(callback.message.chat.id, LANGUAGES['en']['database_error'])
        await state.clear()
        await timer_manager.cancel_timer_task(callback.message.chat.id)
    except Exception as e:
        logger.error(f"unable to add a user in {callback.message.chat.id}: {e}")
        await bot.send_message(callback.message.chat.id, LANGUAGES['en']['general_error'])
        await state.clear()
        await timer_manager.cancel_timer_task(callback.message.chat.id)
        try: 
            data = {"teams_message": "", "string": "", "main_state": "", "start_message": "", "teams": {}, "players": [], "timer_task": ""}                
            await rediscli.redis_set_pipeline(callback.message.chat.id, data)
        except RedisError as e:
           logger.error(f"redis unable to add a user in {callback.message.chat.id}: {e}")