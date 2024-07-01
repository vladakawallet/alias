from aiogram.types import BotCommand


private_commands = [
    BotCommand(command="/start", description="start the bot"),
    BotCommand(command="/rules", description="rules of Elias"),
    BotCommand(command="/info", description="review useful information")
]

group_commands = [
    BotCommand(command="/start", description="start the bot"),
    BotCommand(command="/rules", description="rules of Elias"),
    BotCommand(command="/game", description="start to play Elias"),
    BotCommand(command="/cancel", description="cancel game setup"),
    BotCommand(command="/settings", description="Elias settings"),
    BotCommand(command="/info", description="review useful information")
]

# default_commands = [
#     BotCommand(command="/start", description="start the bot"),
#     BotCommand(command="/rules", description="rules of Elias"),
#     BotCommand(command="/info", description="join our community")
# ]