import asyncio
from utils.alias_logger import logger
from redis import RedisError
from utils.languages import LANGUAGES
from aiogram.types import ReplyKeyboardRemove

class AliasTimerManager:
    def __init__(self) -> None:
        from bot_setup import rediscli, bot
        self.rediscli = rediscli
        self.bot = bot
        self.timer_manager = {}

    async def timer(self, chat_id: int | str, duration: int, state: str, prvtchat_id=None, msg_id=None):
        await asyncio.sleep(duration)
        logger.info(f"timer went off on {state}")
        try:
            message_id = await self.rediscli.get_session_field(chat_id, "start_message")
            if state == "setup":
                data = {"main_state": "", "start_message": "", "players": "", "timer_task": ""}
                await self.rediscli.update_session_data(chat_id, data)
                await self.bot.edit_message_text(chat_id=chat_id, text="Час на реєстрацію вичерпано, почніть гру знову!", message_id=message_id)
            elif state == "teams":
                data = {"teams_message": "", "string": "", "main_state": "", "start_message": "", "teams": {}, "players": [], "timer_task": ""}                
                await self.rediscli.redis_set_pipeline(chat_id, data)
                await self.bot.edit_message_text("Визначення команд завершено, вийшов час(2хв.)! Почніть гру знову", chat_id, message_id)
            elif state == "players":
                teams_message_id = await self.rediscli.get_session_field(chat_id, "teams_message")
                await self.bot.delete_message(chat_id, teams_message_id)
                await self.bot.edit_message_text("Визначення команд завершено, вийшов час(2хв.)! Почніть гру знову", chat_id, message_id)
                data = {"teams_message": "", "string": "", "main_state": "", "start_message": "", "teams": {}, "players": [], "timer_task": ""}                
                await self.rediscli.redis_set_pipeline(chat_id, data)
            elif state == "game":
                await self.bot.send_message(chat_id, text="Гру завершено, гравець не відповідає")
                await self.bot.edit_message_text("На жаль, ти не встиг почати гру", prvtchat_id, msg_id)
                data = {"main_state": "", "teams_message": "", "turn": 0, "teams": {}, "start_message": "", "string": "", "players": [], "timer_task": ""}
                await self.rediscli.redis_set_pipeline(chat_id, data)
            elif state.startswith("prvtgame"):
                await self.bot.send_message(chat_id=prvtchat_id, text="Залишилось 15 секунд!")
                await asyncio.sleep(15)
                await self.bot.send_message(chat_id=prvtchat_id, text="Час вийшов, пояснюй останнє слово.")
                msg = await self.bot.send_message(chat_id=chat_id, text="Час вийшов")
                session_data = {"timer_message": msg.message_id, "timer_state": "done"}
                await self.rediscli.update_session_data(chat_id, session_data)
                await asyncio.sleep(3600)
                state = await self.rediscli.get_session_field(chat_id, "main_state")
                try:
                    if state.split()[1] == str(prvtchat_id):
                        await self.bot.send_message(chat_id, "Останнє слово не пояснено, завершаю гру")
                        await self.bot.send_message(prvtchat_id, "Останнє слово не пояснено, завершаю гру", reply_markup=ReplyKeyboardRemove())
                        data = {"main_state": "", "teams_message": "", "turn": 0, "teams": {}, "start_message": "", "string": "", "timer_state": "", "timer_message": ""}
                        await self.rediscli.redis_set_pipeline(chat_id, data)
                except IndexError:
                    pass
        except RedisError as e:
            logger.error(f"redis error on timer: {e}")
            await self.bot.send_message(chat_id, LANGUAGES['en']['database_error'])
        except Exception as e:
            logger.error(f"failed to execute a timer: {e}")
            await self.bot.send_message(chat_id, LANGUAGES['en']['general_error'])


    async def create_timer_task(self, chat_id: int | str, duration: int, state: str, prvtchat_id=None, msg_id=None):
        try: 
            logger.info(f"timer task created on {state}")
            task = asyncio.create_task(self.timer(chat_id, duration, state, prvtchat_id, msg_id))
            self.timer_manager[str(chat_id)] = task
            await self.rediscli.update_session_field(chat_id, "timer_task", state) 
        except RedisError as e:
            logger.error(f"redis failed to create a timer task: {e}")
            await self.bot.send_message(chat_id, LANGUAGES['en']['database_error'])
        except Exception as e:
            logger.error(f"failed to create a timer tasks: {e}")
            await self.bot.send_message(chat_id, LANGUAGES['en']['general_error'])

    async def recreate_timer_task(self, chat_id: int | str, duration: int, next_state: str, prvtchat_id=None, msg_id=None):
        self.timer_manager[str(chat_id)].cancel()
        await self.create_timer_task(chat_id, duration, next_state, prvtchat_id, msg_id)
        # logger.info(f"timer task recreated on {next_state }")

    async def cancel_timer_task(self, chat_id: int | str):
        try:
            if self.timer_manager[str(chat_id)]:
                self.timer_manager[str(chat_id)].cancel()
                del self.timer_manager[str(chat_id)]
        except KeyError:
            pass