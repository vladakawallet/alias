import asyncio
from bot_setup import bot, dp
from handlers import register_handlers
from utils.cmdscopes import private_commands, group_commands
from aiogram.types import BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from aiogram import Bot

async def set_commands(bot: Bot):
    await bot.set_my_commands(private_commands, BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(group_commands, BotCommandScopeAllGroupChats())

async def on_startup():
    await set_commands(bot)


async def bot_start() -> None:
    register_handlers(dp)
    await dp.start_polling(bot, on_startup=on_startup)

if __name__ == "__main__":
    asyncio.run(bot_start())