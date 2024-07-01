from aiogram import Router, F
from aiogram.filters import Command
from aiogram.filters.command import CommandStart
from handlers.start import start_command, bot_status_update
from handlers.setup import game_command, cancel_command
from handlers.teams import teams_mode, team_creation
from handlers.utils import Game, GameSetup, Settings
from handlers.players import delete_on_players, add_user
from handlers.game import start_game_callback, start_privategame_callback
from handlers.processing import correct, incorrect
from handlers.addons import rules_command, info_command
from handlers.settings import settings_command, winscore_callback, new_winscore, roundtimer_callback, new_roundtimer, cancel_settings

def register_handlers(router: Router):
    router.message.register(start_command, CommandStart())
    router.my_chat_member.register(bot_status_update)
    router.message.register(game_command, Command('game'))
    router.message.register(cancel_command, Command('cancel'))
    router.callback_query.register(teams_mode, F.data == "teamsState", )
    router.message.register(team_creation, GameSetup.teams)
    router.message.register(delete_on_players, GameSetup.players)
    router.callback_query.register(add_user, F.data.startswith("set: "), GameSetup.players)
    router.callback_query.register(start_game_callback, F.data == "startGame")
    router.callback_query.register(start_privategame_callback, F.data.startswith("prvtGame: "))
    router.message.register(correct, F.text == "✅", Game.processing)
    router.message.register(incorrect, F.text == "Пропуск❌", Game.processing)
    router.message.register(rules_command, Command('rules'))
    router.message.register(info_command, Command('info'))
    router.message.register(settings_command, Command('settings'))
    router.callback_query.register(winscore_callback, F.data == "winscore", Settings.menu)
    router.message.register(new_winscore, Settings.winscore)
    router.callback_query.register(roundtimer_callback, F.data == "roundtimer", Settings.menu)
    router.message.register(new_roundtimer, Settings.roundtimer)
    router.callback_query.register(cancel_settings, F.data == "cancelsettings", Settings.menu)