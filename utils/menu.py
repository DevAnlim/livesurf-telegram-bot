from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu():
    kb=InlineKeyboardBuilder()
    kb.button(text="👤 Профиль", callback_data="user")
    kb.button(text="📂 Группы", callback_data="groups")
    kb.button(text="📄 Страницы", callback_data="pages")
    kb.button(text="⚙️ Настройки", callback_data="settings")
    kb.adjust(1)
    return kb.as_markup()

def back_menu():
    kb=InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()

