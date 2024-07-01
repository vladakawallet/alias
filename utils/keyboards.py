from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, SwitchInlineQueryChosenChat


language_buttons = [
    [KeyboardButton(text="Українська🇺🇦"), KeyboardButton(text="English🇬🇧"), KeyboardButton(text="Deutsch🇩🇪")]
]
language_keyboard = ReplyKeyboardMarkup(keyboard=language_buttons, resize_keyboard=True, one_time_keyboard=True)


start_buttons = [
    [KeyboardButton(text="Нова гра🎮")],
    [KeyboardButton(text="Правила📚"), KeyboardButton(text="Налаштування⚙")]
]

startgroup_inline_btn = [
    [InlineKeyboardButton(text="Нова гра🎮", callback_data="newGame"),
    InlineKeyboardButton(text="Правила📚", callback_data="rules"),],
    [InlineKeyboardButton(text="Налаштування⚙", callback_data="settings")]
]

startgroup_inline_kb = InlineKeyboardMarkup(inline_keyboard=startgroup_inline_btn)

start_kb = ReplyKeyboardMarkup(keyboard=start_buttons, resize_keyboard=True)

start_inline_btn = [[InlineKeyboardButton(text="Додати бота у один з ваших чатів",
                                        switch_inline_query_chosen_chat=SwitchInlineQueryChosenChat(query="/start@AIiasBot", allow_group_chats=True),
                                        url="https://t.me/AIiasBot?startgroup")]]
                                        
start_inline_kb = InlineKeyboardMarkup(inline_keyboard=start_inline_btn)

invite_alias_link_btn = [[InlineKeyboardButton(text="Приєднатися", callback_data="inviteTrue", url="https://t.me/{bot_username}?start=from_group")]]
invite_alias_link_kb = InlineKeyboardMarkup(inline_keyboard=invite_alias_link_btn)

invite_start_link_btn = [
    [InlineKeyboardButton(text="Приєднатися", callback_data="inviteTrue")],
    [InlineKeyboardButton(text="Визначити команди🎮", callback_data="teamsState")]
]
invite_start_link_kb = InlineKeyboardMarkup(inline_keyboard=invite_start_link_btn)

settings_inline_btns = [[InlineKeyboardButton(text="Winscore", callback_data="winscore")],[InlineKeyboardButton(text="Roundtimer", callback_data="roundtimer"),],
                        # [InlineKeyboardButton(text="Language", callback_data="language"),],
                        [InlineKeyboardButton(text="Cancel", callback_data="cancelsettings")]]
settings_inline_kb = InlineKeyboardMarkup(inline_keyboard=settings_inline_btns)
# settings_btn = [
#     [InlineKeyboardButton(text="Тривалість раунду⏰")],
#     [InlineKeyboardButton(text="Переможний ліміт🎯")], 
#     [InlineKeyboardButton(text="Мова інтерфейсу🌐")]
# ]
# settings_kb = InlineKeyboardMarkup(keyboard=settings_btn, )

KEYBOARDS = {  
}