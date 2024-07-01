from bot_setup import bot, logger, rediscli
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import CommandObject
from aiogram.enums.parse_mode import ParseMode
import base64
import utils.keyboards as keyboards
from utils.languages import LANGUAGES
from redis import RedisError
from handlers.setup import accept_invite_query
from handlers.utils import check_bot_admin


async def start_command(message: Message, command: CommandObject):
    try:
        if command.args:
            decoded_args = base64.b64decode(command.args).decode('utf-8')
            _, chat_id = decoded_args.split('|')
            print(command.args)
            await accept_invite_query(chat_id, message.from_user.first_name, message.from_user.id)
            await message.answer("Ти приєднався до гри в Еліас")
            return
        if message.chat.type == 'private':
            await message.answer(LANGUAGES['uk']['private_greeting'].format(name=message.from_user.first_name),
                                reply_markup=keyboards.start_inline_kb, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"{message.from_user.username} has started a bot")
        elif message.chat.type == 'group' or message.chat.type == 'supergroup':
            if await check_bot_admin(message.chat.id):    
                main_state = await rediscli.get_session_field(message.chat.id, "main_state")
                if main_state in ["teams", "setup", "game", "players"] or main_state.startswith("prvtgame"):
                    await bot.delete_message(message.chat.id, message.message_id)
                else:
                    if await rediscli.check_existed_session(message.chat.id) == False:
                        await rediscli.init_session(message.chat.id)
                        logger.info(f"session is created on {message.chat.id}")
                    await message.answer(LANGUAGES['uk']['group_greeting_admin'], parse_mode=ParseMode.MARKDOWN)
            else:
                await message.answer(LANGUAGES['uk']['group_greeting'], parse_mode=ParseMode.MARKDOWN)
            logger.info(f"bot is started in group {message.chat.id}")
    except RedisError as e:
        logger.error(f"redis error on start command in {message.chat.id}: {e}")
        await message.answer(LANGUAGES['en']['database_error'])
    except Exception as e:
        logger.error(f"an error on start command in {message.chat.id}: {e}")
        await message.answer(LANGUAGES['en']['general_error'])


async def bot_status_update(update: ChatMemberUpdated):
    try:
        if update.new_chat_member.user.id == bot.id and update.new_chat_member.status != "kicked":
            if await check_bot_admin(update.chat.id):
                if update.old_chat_member.status not in ["member", "administrator"]:
                    await update.answer(LANGUAGES['uk']['group_greeting_admin'], parse_mode=ParseMode.MARKDOWN)   
                    await rediscli.init_session(update.chat.id)
                    logger.info(f"bot is added into {update.chat.id}")
                    logger.info(f"session is created on {update.chat.id}")
                else:
                    await update.answer(LANGUAGES['uk']['group_greeting_admin_after_member'])
                    if await rediscli.check_existed_session(update.chat.id) == False:
                        await rediscli.init_session(update.chat.id)
                        logger.info(f"session is created on {update.chat.id}")
            elif update.new_chat_member.status == "administrator" or update.new_chat_member.status == "member" and update.old_chat_member.status in ["member", "administrator"]:
                await update.answer(LANGUAGES['uk']['bot_is_still_member'], parse_mode=ParseMode.MARKDOWN)
            else:
                await update.answer(LANGUAGES['uk']['group_greeting'], parse_mode=ParseMode.MARKDOWN)
                logger.info(f"bot is added into {update.chat.id}")   
        elif update.new_chat_member.status == "kicked":
            await rediscli.delete_session(update.chat.id)
            logger.info(f"bot was kicked from {update.chat.id}")
    except RedisError as e:
        logger.error(f"redis failed to init a session on member update in {update.chat.id}: {e}")
        await update.answer(LANGUAGES['en']['database_error'])
    except Exception as e:
        logger.error(f"an error on member update in {update.chat.id}: {e}")
        await update.answer(LANGUAGES['en']['general_error'])