import asyncio, json, os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.storage import set_api_key,get_api_key,delete_api_key
from utils.menu import main_menu,back_menu
from livesurf_sdk.api import LiveSurfApi

TELEGRAM_BOT_TOKEN= "Тут Токен бота телеграм"
bot=Bot(token=TELEGRAM_BOT_TOKEN,parse_mode="HTML")
dp=Dispatcher(storage=MemoryStorage())

# ---------------------- Форматирование ----------------------
def format_user_profile(data:dict)->str:
    workmode="Авто" if data.get("workmode")==1 else "Ручной"
    status="Активен ✅" if data.get("is_active") else "Неактивен ❌"
    return (f"👤 <b>Профиль</b>\n💰 Кредиты: {int(float(data.get('credits')))}\n⚙️ Режим: {workmode}\n"
            f"🏆 Опыт: {data.get('experience')}\n🔑 Токен: {data.get('token')[:8]}...{data.get('token')[-8:]}\n"
            f"🟢 Статус: {status}")

def format_groups_list(groups:list)->str:
    text="📂 <b>Группы</b>:\n\n"
    for g in groups:
        name=g.get("name") or g.get("title") or "Без названия"
        text+=f"• {name}\n"
    return text

def format_group_details(group:dict)->str:
    lines=[f"📁 <b>{group.get('name')}</b>",
           f"⏱ Лимит по часу: {group.get('hour_limit')}",
           f"📅 Лимит по дню: {group.get('day_limit')}",
           f"🌐 Уникальные IP: {group.get('uniq_ip')}",
           f"📊 Коэф. мобилизации: {group.get('moby_ratio')}%",
           f"🗺 Гео: {', '.join(map(str, group.get('geo',[])))}",
           f"⏰ Часы остановки: {', '.join(map(str,group.get('stopping_hours',[])))}",
           f"⏳ Авторасчёт: {'Да' if group.get('autocalc_visits',{}).get('enabled') else 'Нет'}",
           f"⏰ Часовой пояс: {group.get('timezone')}",
           f"💳 Кредиты: {group.get('credits')}"]
    sources=group.get("sources",{})
    src_lines=[f"{k.capitalize()}: {v.get('value')}" for k,v in sources.items() if v.get("enabled")]
    if src_lines: lines.append("\n<b>Источники:</b>"); lines.extend(src_lines)
    pages=group.get("pages",[])
    if pages: lines.append("\n<b>Страницы:</b>")
    for p in pages: lines.append(f"• {', '.join(p.get('url',[]))} (Время показа: {p.get('showtime',[0,0])[0]}s)")
    return "\n".join(lines)

def format_page(page:dict)->str:
    state="Активна ✅" if page.get("state")==1 else "Остановлена ⏹"
    urls=", ".join(page.get("url",[]))
    return f"📄 <b>Страница</b>\nURL: {urls}\nShowtime: {page.get('showtime',[0,0])[0]}s\nСостояние: {state}"

# ---------------------- Состояния ----------------------
class CreateGroupStates(StatesGroup):
    waiting_name=State()
    waiting_opts=State()
class AddCreditsStates(StatesGroup):
    waiting_amount=State()

# ---------------------- Хендлеры ----------------------
@dp.message(Command("start"))
async def cmd_start(message:types.Message,state:FSMContext):
    api_key=get_api_key(message.from_user.id)
    if api_key: await message.answer("Добро пожаловать! Меню:",reply_markup=main_menu())
    else: await message.answer("Привет! Отправь мне свой LiveSurf API ключ.")

@dp.message()
async def handle_message(message:types.Message):
    existing=get_api_key(message.from_user.id)
    if not existing:
        set_api_key(message.from_user.id,message.text.strip())
        await message.answer("✅ Ключ сохранён. Меню:",reply_markup=main_menu())
    else:
        await message.answer("Выберите действие в меню.",reply_markup=main_menu())

@dp.callback_query(lambda c: True)
async def callbacks_handler(callback:types.CallbackQuery,state:FSMContext):
    data=callback.data; user_id=callback.from_user.id; api_key=get_api_key(user_id)
    if data=="back_to_main": await callback.message.edit_text("Меню:",reply_markup=main_menu()); await callback.answer(); return
    if not api_key: await callback.message.answer("Сначала отправьте API-ключ"); await callback.answer(); return
    api=LiveSurfApi(api_key)

    # --------- Профиль ---------
    if data=="user":
        try: res=await asyncio.to_thread(api.get_user)
        except Exception as e: await callback.message.edit_text(f"Ошибка: {e}",reply_markup=back_menu()); await callback.answer(); return
        await callback.message.edit_text(format_user_profile(res),reply_markup=back_menu()); await callback.answer()

    # --------- Группы ---------
    elif data=="groups":
        try: res=await asyncio.to_thread(api.get_groups)
        except Exception as e: await callback.message.edit_text(f"Ошибка: {e}",reply_markup=back_menu()); await callback.answer(); return
        text=format_groups_list(res)
        kb=InlineKeyboardBuilder()
        for g in res: kb.button(text=g.get("name") or g.get("title") or "Без названия",callback_data=f"show_group:{g.get('id')}")
        kb.button(text="⬅️ Назад",callback_data="back_to_main"); kb.adjust(1)
        await callback.message.edit_text(text,reply_markup=kb.as_markup()); await callback.answer()

    # --------- Детали группы ---------
    elif data and data.startswith("show_group:"):
        gid=data.split(":",1)[1]; await callback.message.edit_text("Загружаю...",reply_markup=back_menu())
        try:
            grp=await asyncio.to_thread(api.get_group,int(gid))
            kb=InlineKeyboardBuilder()
            for p in grp.get("pages",[]): kb.button(text=f"Страница {p.get('id')}",callback_data=f"show_page:{p.get('id')}:{gid}")
            kb.button(text="⬅️ Назад",callback_data="groups")
            kb.adjust(1)
            await callback.message.edit_text(format_group_details(grp),reply_markup=kb.as_markup())
        except Exception as e: await callback.message.edit_text(f"Ошибка: {e}",reply_markup=back_menu())
        await callback.answer()

    # --------- Страница ---------
    elif data and data.startswith("show_page:"):
        parts=data.split(":"); pid=int(parts[1]); gid=int(parts[2])
        try:
            grp=await asyncio.to_thread(api.get_group,gid)
            page=next((p for p in grp.get("pages",[]) if p.get("id")==pid), None)
            if not page: raise Exception("Страница не найдена")
            kb=InlineKeyboardBuilder()
            kb.button(text="🚀 Запустить",callback_data=f"start_page:{pid}")
            kb.button(text="⏹ Остановить",callback_data=f"stop_page:{pid}")
            kb.button(text="📄 Клонировать",callback_data=f"clone_page:{pid}")
            kb.button(text="🗑 Удалить",callback_data=f"delete_page:{pid}")
            kb.button(text="⬅️ Назад",callback_data=f"show_group:{gid}")
            kb.adjust(1)
            await callback.message.edit_text(format_page(page),reply_markup=kb.as_markup())
        except Exception as e: await callback.message.edit_text(f"Ошибка: {e}",reply_markup=back_menu())
        await callback.answer()

    # --------- Управление страницами ---------
    elif data and data.startswith("start_page:"):
        pid=int(data.split(":")[1])
        try: await asyncio.to_thread(api.start_page,pid); await callback.message.answer("Страница запущена ✅")
        except Exception as e: await callback.message.answer(f"Ошибка: {e}")
        await callback.answer(); await callback.message.delete()
    elif data and data.startswith("stop_page:"):
        pid=int(data.split(":")[1])
        try: await asyncio.to_thread(api.stop_page,pid); await callback.message.answer("Страница остановлена ⏹")
        except Exception as e: await callback.message.answer(f"Ошибка: {e}")
        await callback.answer(); await callback.message.delete()
    elif data and data.startswith("clone_page:"):
        pid=int(data.split(":")[1])
        try: await asyncio.to_thread(api.clone_page,pid); await callback.message.answer("Страница склонирована 📄")
        except Exception as e: await callback.message.answer(f"Ошибка: {e}")
        await callback.answer(); await callback.message.delete()
    elif data and data.startswith("delete_page:"):
        pid=int(data.split(":")[1])
        try: await asyncio.to_thread(api.delete_page,pid); await callback.message.answer("Страница удалена 🗑")
        except Exception as e: await callback.message.answer(f"Ошибка: {e}")
        await callback.answer(); await callback.message.delete()

    # --------- Настройки ---------
    elif data=="settings":
        kb=InlineKeyboardBuilder()
        kb.button(text="Удалить API-ключ",callback_data="del_api_key"); kb.button(text="⬅️ Назад",callback_data="back_to_main")
        kb.adjust(1); await callback.message.edit_text("Настройки:",reply_markup=kb.as_markup()); await callback.answer()
    elif data=="del_api_key":
        delete_api_key(user_id); await callback.message.edit_text("Ключ удалён. Отправьте новый.",reply_markup=None); await callback.answer()
    else: await callback.answer()

# ---------------------- Запуск ----------------------
if __name__=="__main__":
    import logging; logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))

