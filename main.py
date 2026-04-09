import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# --- КОНФІГУРАЦІЯ ---
API_TOKEN = os.getenv("BOT_TOKEN")
SUPER_ADMIN_ID = 609022216 

DEPT_ADMINS = {
    "rights": 0,    
    "sex_ed": 0,    
    "mental": 0,    
    "leisure": 0,   
    "bullying": 0,
    "cyber": 0      # <--- НОВИЙ ВІДДІЛ (Впиши сюди ID адміна кібербезпеки)
}

DEPT_NAMES = {
    "rights": "⚖️ Недодержання прав дитини",
    "sex_ed": "❤️ Сексуальна освіта та насилля",
    "mental": "🧠 Ментальне здоровʼя",
    "leisure": "🎨 Якісне дозвілля",
    "bullying": "🚫 Булінг",
    "cyber": "🔐 Кібербезпека" # <--- НОВА НАЗВА
}

# --- ІНІЦІАЛІЗАЦІЯ ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())

# --- МАШИНА СТАНІВ ---
class ReportForm(StatesGroup):
    choosing_dept = State()
    choosing_type = State()
    writing_text = State()
    choosing_anonymity = State()
    writing_name = State()
    choosing_contact_type = State()
    writing_contact = State()

# --- КЛАВІАТУРИ (Тільки Inline) ---

def add_navigation(keyboard_rows):
    # Додаємо ряд кнопок навігації
    nav_row = [
        InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_back"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="nav_menu")
    ]
    keyboard_rows.append(nav_row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

def get_dept_keyboard():
    rows = [
        [InlineKeyboardButton(text="⚖️ Права дитини", callback_data="dept_rights")],
        [InlineKeyboardButton(text="❤️ Секс. освіта / Насилля", callback_data="dept_sex_ed")],
        [InlineKeyboardButton(text="🧠 Ментальне здоровʼя", callback_data="dept_mental")],
        [InlineKeyboardButton(text="🎨 Якісне дозвілля", callback_data="dept_leisure")],
        [InlineKeyboardButton(text="🚫 Булінг", callback_data="dept_bullying")],
        [InlineKeyboardButton(text="🔐 Кібербезпека", callback_data="dept_cyber")] # <--- НОВА КНОПКА
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_type_keyboard():
    rows = [
        [InlineKeyboardButton(text="🆘 Потрібна допомога", callback_data="type_help")],
        [InlineKeyboardButton(text="📢 Повідомити про порушення", callback_data="type_report")],
        [InlineKeyboardButton(text="💡 Запропонувати ідею", callback_data="type_idea")]
    ]
    return add_navigation(rows)

def get_anon_keyboard():
    rows = [
        [InlineKeyboardButton(text="🕵️ Надіслати анонімно", callback_data="anon_yes")],
        [InlineKeyboardButton(text="📝 Вказати свої дані", callback_data="anon_no")]
    ]
    return add_navigation(rows)

def get_contact_type_keyboard():
    rows = [
        [InlineKeyboardButton(text="📱 Номер телефону", callback_data="cont_phone")],
        [InlineKeyboardButton(text="✈️ Telegram", callback_data="cont_tg")],
        [InlineKeyboardButton(text="📧 Email", callback_data="cont_email")]
    ]
    return add_navigation(rows)

def get_only_nav_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_back"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="nav_menu")
    ]])

# --- НАВІГАЦІЯ ---

@dp.callback_query(F.data == "nav_menu")
async def nav_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "🇺🇦 *Головне меню*\n\n"
        "👇 *Обери відділ для звернення:*"
    )
    await callback.message.edit_text(text, reply_markup=get_dept_keyboard())
    await state.set_state(ReportForm.choosing_dept)

@dp.callback_query(F.data == "nav_back")
async def nav_back_handler(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state == ReportForm.choosing_type:
        await nav_menu_handler(callback, state)
        
    elif current_state == ReportForm.writing_text:
        data = await state.get_data()
        dept_name = DEPT_NAMES.get(data.get("dept"))
        await callback.message.edit_text(
            f"Напрямок: *{dept_name}*\nОбери тип звернення:", 
            reply_markup=get_type_keyboard()
        )
        await state.set_state(ReportForm.choosing_type)
        
    elif current_state == ReportForm.choosing_anonymity:
        await callback.message.edit_text(
            "✍️ *Напиши своє повідомлення:*",
            reply_markup=get_only_nav_keyboard()
        )
        await state.set_state(ReportForm.writing_text)
        
    elif current_state == ReportForm.writing_name:
        await callback.message.edit_text(
            "Це звернення анонімне чи з контактами?",
            reply_markup=get_anon_keyboard()
        )
        await state.set_state(ReportForm.choosing_anonymity)
        
    elif current_state == ReportForm.choosing_contact_type:
        await callback.message.edit_text(
            "Введи своє *Прізвище та Ім'я*:",
            reply_markup=get_only_nav_keyboard()
        )
        await state.set_state(ReportForm.writing_name)
        
    elif current_state == ReportForm.writing_contact:
        await callback.message.edit_text(
            "Обери тип контакту:",
            reply_markup=get_contact_type_keyboard()
        )
        await state.set_state(ReportForm.choosing_contact_type)
    
    else:
        await nav_menu_handler(callback, state)

# --- ЛОГІКА ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🇺🇦 *Вітаємо!*\n"
        "Це бот *Національної молодіжної ради*.\n\n"
        "👇 *Обери відділ для звернення:*",
        reply_markup=get_dept_keyboard()
    )
    msg = await message.answer("...", reply_markup=ReplyKeyboardRemove())
    await msg.delete()
    
    await state.set_state(ReportForm.choosing_dept)

@dp.callback_query(StateFilter(ReportForm.choosing_dept), F.data.startswith("dept_"))
async def step_dept(callback: types.CallbackQuery, state: FSMContext):
    dept_code = callback.data.split("_", 1)[1]
    await state.update_data(dept=dept_code)
    dept_name = DEPT_NAMES.get(dept_code)
    
    await callback.message.edit_text(
        f"Напрямок: *{dept_name}*\nОбери тип звернення:",
        reply_markup=get_type_keyboard()
    )
    await state.set_state(ReportForm.choosing_type)

@dp.callback_query(StateFilter(ReportForm.choosing_type), F.data.startswith("type_"))
async def step_type(callback: types.CallbackQuery, state: FSMContext):
    types_map = {"type_help": "🆘 Запит на допомогу", "type_report": "📢 Проблема", "type_idea": "💡 Ідея"}
    await state.update_data(msg_type=types_map.get(callback.data))
    
    await callback.message.edit_text(
        "✍️ *Напиши своє повідомлення:*",
        reply_markup=get_only_nav_keyboard()
    )
    await state.set_state(ReportForm.writing_text)

@dp.message(StateFilter(ReportForm.writing_text))
async def step_text(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Будь ласка, надішли текст.", reply_markup=get_only_nav_keyboard())
        return
    await state.update_data(main_text=message.text)
    await message.answer(
        "Бажаєш залишити контакти?",
        reply_markup=get_anon_keyboard()
    )
    await state.set_state(ReportForm.choosing_anonymity)

@dp.callback_query(StateFilter(ReportForm.choosing_anonymity))
async def step_anon(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "anon_yes":
        await finalize_report(callback.message, state)
    else:
        await callback.message.edit_text(
            "Введи *Прізвище та Ім'я*:",
            reply_markup=get_only_nav_keyboard()
        )
        await state.set_state(ReportForm.writing_name)

@dp.message(StateFilter(ReportForm.writing_name))
async def step_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name.split()) < 2 or len(name) < 5:
        await message.answer("⚠️ Введи повне Ім'я та Прізвище.", reply_markup=get_only_nav_keyboard())
        return
    await state.update_data(user_name=name)
    await message.answer(
        "Обери тип контакту:",
        reply_markup=get_contact_type_keyboard()
    )
    await state.set_state(ReportForm.choosing_contact_type)

@dp.callback_query(StateFilter(ReportForm.choosing_contact_type))
async def step_contact_type(callback: types.CallbackQuery, state: FSMContext):
    ctype = callback.data
    await state.update_data(contact_type=ctype)
    prompt = "Введи дані:"
    if ctype == "cont_phone": prompt = "📞 Введи номер:"
    elif ctype == "cont_tg": prompt = "✈️ Введи нік (@name):"
    elif ctype == "cont_email": prompt = "📧 Введи email:"
    
    await callback.message.edit_text(prompt, reply_markup=get_only_nav_keyboard())
    await state.set_state(ReportForm.writing_contact)

@dp.message(StateFilter(ReportForm.writing_contact))
async def step_contact_val(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ctype = data.get("contact_type")
    content = message.text.strip()
    valid, error = True, ""

    if ctype == "cont_phone":
        if not (re.sub(r'\D', '', content) and 9 <= len(re.sub(r'\D', '', content)) <= 13):
            valid, error = False, "Невірний номер."
    elif ctype == "cont_tg":
        if "@" not in content and "t.me" not in content:
            valid, error = False, "Потрібен @нік."
    elif ctype == "cont_email":
        if "@" not in content:
            valid, error = False, "Невірний email."

    if not valid:
        await message.answer(f"⚠️ {error} Спробуй ще раз:", reply_markup=get_only_nav_keyboard())
        return

    await state.update_data(user_contact=content)
    await finalize_report(message, state)

async def finalize_report(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dept_name = DEPT_NAMES.get(data.get("dept"), "Інше")
    msg_type = data.get("msg_type")
    text = data.get("main_text")
    
    author = f"👤 *{data.get('user_name')}*\n📞 `{data.get('user_contact')}`" if data.get("user_name") else "🕵️ *Анонімно*"

    admin_msg = (
        f"🔔 *НОВЕ ЗВЕРНЕННЯ*\n➖➖➖➖➖\n"
        f"🏢 *{dept_name}*\n📌 *{msg_type}*\n➖➖➖➖➖\n\n"
        f"{text}\n\n➖➖➖➖➖\n{author}"
    )

    try: await bot.send_message(SUPER_ADMIN_ID, admin_msg)
    except: pass

    dept_admin = DEPT_ADMINS.get(data.get("dept"))
    if dept_admin:
        try: await bot.send_message(dept_admin, admin_msg)
        except: pass

    await message.answer(
        "✅ *Повідомлення надіслано!*",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data="nav_menu")]])
    )
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())