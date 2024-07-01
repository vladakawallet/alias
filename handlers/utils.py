from bot_setup import bot, logger
from aiogram.fsm.state import StatesGroup, State

async def check_bot_admin(chat_id):
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins: 
            if admin.user.id == bot.id:
                if admin.can_delete_messages and admin.can_pin_messages and admin.can_restrict_members:
                    return True
            return False
    except Exception as e:
        logger.error(f"failed to check bot\'s status in {chat_id}: {e}")

        
class GameSetup(StatesGroup):
    teams = State()
    players = State()

class Game(StatesGroup):
    processing = State()

class Settings(StatesGroup):
    menu = State()
    winscore = State()
    roundtimer = State()
    language = State()