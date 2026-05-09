BOT_TOKEN = "8724276114:AAEEk6WlEtY91WJ-aaRaJlAGCFr8pAMrDEM"
OWNER_ID = 8378615092
import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove,
)

import data


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)


def get_role(user_id):
    if user_id == OWNER_ID: return "owner"
    if data.is_admin(user_id): return "admin"
    if data.is_support(user_id): return "support"
    return "user"


class AddMovie(StatesGroup):
    waiting_code = State(); waiting_file = State()
class DeleteMovie(StatesGroup):
    waiting_code = State()
class AddAdmin(StatesGroup):
    waiting_id = State()
class RemoveAdmin(StatesGroup):
    waiting_id = State()
class AddSupport(StatesGroup):
    waiting_id = State()
class RemoveSupport(StatesGroup):
    waiting_id = State()
class AddChannel(StatesGroup):
    waiting_channel = State()
class RemoveChannel(StatesGroup):
    waiting_channel = State()
class Broadcast(StatesGroup):
    waiting_message = State()


def main_kb(user_id):
    buttons = [[KeyboardButton(text="🎬 Kino qidirish")]]
    if get_role(user_id) in ("owner", "admin", "support"):
        buttons.append([KeyboardButton(text="⚙️ Admin panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def admin_kb(user_id):
    role = get_role(user_id)
    buttons = [
        [KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="🗑 Kino o'chirish")],
        [KeyboardButton(text="📢 Reklama"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📡 Majburiy obuna")],
    ]
    if role in ("owner", "admin"):
        buttons.append([KeyboardButton(text="👤 Admin qo'shish"), KeyboardButton(text="❌ Admin o'chirish")])
        buttons.append([KeyboardButton(text="🤝 Support qo'shish"), KeyboardButton(text="➖ Support o'chirish")])
    buttons.append([KeyboardButton(text="🔙 Orqaga")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def channel_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Kanal qo'shish"), KeyboardButton(text="🗑 Kanal o'chirish")],
        [KeyboardButton(text="📋 Kanallar ro'yxati")],
        [KeyboardButton(text="🔙 Orqaga")],
    ], resize_keyboard=True)

def check_sub_kb(channels):
    buttons = []
    for ch in channels:
        username = ch if ch.startswith("@") else f"@{ch.lstrip('@')}"
        buttons.append([InlineKeyboardButton(text=f"📢 {username}", url=f"https://t.me/{username.lstrip('@')}")])
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def check_subscriptions(bot, user_id):
    channels = data.get_all_channels()
    if not channels: return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status in ("left", "kicked", "banned"): return False
        except Exception as e:
            logger.warning("Kanal xato (%s): %s", ch, e)
    return True

async def send_subscribe_message(message, channels):
    text = "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n\n" + "\n".join(f"• {ch}" for ch in channels)
    await message.answer(text, reply_markup=check_sub_kb(channels))


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if not data.user_exists(user_id):
        data.add_user(user_id, message.from_user.full_name, message.from_user.username)
    channels = data.get_all_channels()
    if channels and not await check_subscriptions(message.bot, user_id):
        await send_subscribe_message(message, channels); return
    role_text = {"owner": "👑 Owner", "admin": "🛡 Admin", "support": "🤝 Support"}.get(get_role(user_id), "👤 Foydalanuvchi")
    await message.answer(f"Salom, {message.from_user.full_name}! 👋\nRolingiz: {role_text}\n\n🎬 Kino kodini yuboring.", reply_markup=main_kb(user_id))

@router.callback_query(F.data == "check_sub")
async def cb_check_sub(call: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = call.from_user.id
    if await check_subscriptions(call.bot, user_id):
        await call.message.delete()
        role_text = {"owner": "👑 Owner", "admin": "🛡 Admin", "support": "🤝 Support"}.get(get_role(user_id), "👤 Foydalanuvchi")
        await call.message.answer(f"✅ Obuna tasdiqlandi!\nSalom, {call.from_user.full_name}!\nRolingiz: {role_text}\n\n🎬 Kino kodini yuboring.", reply_markup=main_kb(user_id))
    else:
        await call.answer("❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin", "support"):
        await message.answer("❌ Ruxsat yo'q."); return
    await message.answer("⚙️ Admin panel:", reply_markup=admin_kb(message.from_user.id))

@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin", "support"):
        await message.answer("❌ Ruxsat yo'q."); return
    await send_statistics(message)

@router.message(F.text == "⚙️ Admin panel")
async def panel_handler(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin", "support"):
        await message.answer("❌ Ruxsat yo'q."); return
    await message.answer("⚙️ Admin panel:", reply_markup=admin_kb(message.from_user.id))

@router.message(F.text == "🔙 Orqaga")
async def back_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Asosiy menyu:", reply_markup=main_kb(message.from_user.id))

@router.message(F.text == "🎬 Kino qidirish")
async def movie_search_prompt(message: Message, state: FSMContext):
    await state.clear()
    channels = data.get_all_channels()
    if channels and not await check_subscriptions(message.bot, message.from_user.id):
        await send_subscribe_message(message, channels); return
    await message.answer("🔢 Kino kodini kiriting:", reply_markup=ReplyKeyboardRemove())

@router.message(F.text == "➕ Kino qo'shish")
async def add_movie_start(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin", "support"):
        await message.answer("❌ Ruxsat yo'q."); return
    await state.set_state(AddMovie.waiting_code)
    await message.answer("🔢 Yangi kino uchun kod kiriting:", reply_markup=ReplyKeyboardRemove())

@router.message(AddMovie.waiting_code)
async def add_movie_code(message: Message, state: FSMContext):
    code = message.text.strip()
    if data.movie_exists(code):
        await message.answer(f"⚠️ '{code}' kodi allaqachon mavjud."); return
    await state.update_data(code=code)
    await state.set_state(AddMovie.waiting_file)
    await message.answer("🎬 Kino faylini yuboring (video yoki document):")

@router.message(AddMovie.waiting_file, F.video | F.document)
async def add_movie_file(message: Message, state: FSMContext):
    code = (await state.get_data())["code"]
    if message.video: file_id, file_type = message.video.file_id, "video"
    else: file_id, file_type = message.document.file_id, "document"
    data.add_movie(code, file_id, file_type)
    await state.clear()
    await message.answer(f"✅ Kino qo'shildi!\n📌 Kod: <code>{code}</code>", parse_mode=ParseMode.HTML, reply_markup=admin_kb(message.from_user.id))

@router.message(AddMovie.waiting_file)
async def add_movie_file_wrong(message: Message, state: FSMContext):
    await message.answer("❌ Iltimos, video yoki fayl yuboring.")

@router.message(F.text == "🗑 Kino o'chirish")
async def delete_movie_start(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin", "support"):
        await message.answer("❌ Ruxsat yo'q."); return
    await state.set_state(DeleteMovie.waiting_code)
    await message.answer("🔢 O'chirmoqchi bo'lgan kino kodini kiriting:", reply_markup=ReplyKeyboardRemove())

@router.message(DeleteMovie.waiting_code)
async def delete_movie_code(message: Message, state: FSMContext):
    code = message.text.strip()
    if not data.delete_movie(code):
        await message.answer(f"❌ '{code}' kodli kino topilmadi."); return
    await state.clear()
    await message.answer(f"✅ '{code}' kodli kino o'chirildi.", reply_markup=admin_kb(message.from_user.id))

@router.message(F.text == "👤 Admin qo'shish")
async def add_admin_start(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin"):
        await message.answer("❌ Ruxsat yo'q."); return
    await state.set_state(AddAdmin.waiting_id)
    await message.answer("🆔 Admin qilmoqchi bo'lgan foydalanuvchining ID sini kiriting:", reply_markup=ReplyKeyboardRemove())

@router.message(AddAdmin.waiting_id)
async def add_admin_id(message: Message, state: FSMContext):
    try: target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID."); return
    if target_id == OWNER_ID:
        await state.clear(); await message.answer("❌ Owner ni admin qilib bo'lmaydi.", reply_markup=admin_kb(message.from_user.id)); return
    if not data.user_exists(target_id):
        await message.answer("❌ Bu foydalanuvchi /start bosmagan."); return
    if data.is_admin(target_id):
        await state.clear(); await message.answer("⚠️ Allaqachon admin.", reply_markup=admin_kb(message.from_user.id)); return
    if data.is_support(target_id): data.remove_support(target_id)
    data.add_admin(target_id)
    await state.clear()
    await message.answer(f"✅ {target_id} admin qilindi.", reply_markup=admin_kb(message.from_user.id))

@router.message(F.text == "❌ Admin o'chirish")
async def remove_admin_start(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin"):
        await message.answer("❌ Ruxsat yo'q."); return
    admins = data.get_all_admins()
    if not admins:
        await message.answer("📋 Adminlar yo'q.", reply_markup=admin_kb(message.from_user.id)); return
    await state.set_state(RemoveAdmin.waiting_id)
    await message.answer("📋 Adminlar:\n" + "\n".join(f"• <code>{a}</code>" for a in admins) + "\n\nID ni kiriting:", parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())

@router.message(RemoveAdmin.waiting_id)
async def remove_admin_id(message: Message, state: FSMContext):
    try: target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID."); return
    if not data.remove_admin(target_id):
        await message.answer("❌ Bu foydalanuvchi admin emas."); return
    await state.clear()
    await message.answer(f"✅ {target_id} admin lavozimidan olindi.", reply_markup=admin_kb(message.from_user.id))

@router.message(F.text == "🤝 Support qo'shish")
async def add_support_start(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin"):
        await message.answer("❌ Ruxsat yo'q."); return
    await state.set_state(AddSupport.waiting_id)
    await message.answer("🆔 Support qilmoqchi bo'lgan foydalanuvchining ID sini kiriting:", reply_markup=ReplyKeyboardRemove())

@router.message(AddSupport.waiting_id)
async def add_support_id(message: Message, state: FSMContext):
    try: target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID."); return
    if target_id == OWNER_ID:
        await state.clear(); await message.answer("❌ Owner ni support qilib bo'lmaydi.", reply_markup=admin_kb(message.from_user.id)); return
    if not data.user_exists(target_id):
        await message.answer("❌ Bu foydalanuvchi /start bosmagan."); return
    if data.is_support(target_id):
        await state.clear(); await message.answer("⚠️ Allaqachon support.", reply_markup=admin_kb(message.from_user.id)); return
    if data.is_admin(target_id):
        await state.clear(); await message.answer("⚠️ Bu foydalanuvchi admin.", reply_markup=admin_kb(message.from_user.id)); return
    data.add_support(target_id)
    await state.clear()
    await message.answer(f"✅ {target_id} support qilindi.", reply_markup=admin_kb(message.from_user.id))

@router.message(F.text == "➖ Support o'chirish")
async def remove_support_start(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin"):
        await message.answer("❌ Ruxsat yo'q."); return
    supports = data.get_all_supports()
    if not supports:
        await message.answer("📋 Supportlar yo'q.", reply_markup=admin_kb(message.from_user.id)); return
    await state.set_state(RemoveSupport.waiting_id)
    await message.answer("📋 Supportlar:\n" + "\n".join(f"• <code>{s}</code>" for s in supports) + "\n\nID ni kiriting:", parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())

@router.message(RemoveSupport.waiting_id)
async def remove_support_id(message: Message, state: FSMContext):
    try: target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID."); return
    if not data.remove_support(target_id):
        await message.answer("❌ Bu foydalanuvchi support emas."); return
    await state.clear()
    await message.answer(f"✅ {target_id} support lavozimidan olindi.", reply_markup=admin_kb(message.from_user.id))

@router.message(F.text == "📡 Majburiy obuna")
async def channels_panel(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin", "support"):
        await message.answer("❌ Ruxsat yo'q."); return
    await message.answer("📡 Majburiy obuna boshqaruvi:", reply_markup=channel_kb())

@router.message(F.text == "➕ Kanal qo'shish")
async def add_channel_start(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin", "support"):
        await message.answer("❌ Ruxsat yo'q."); return
    await state.set_state(AddChannel.waiting_channel)
    await message.answer("📢 Kanal username yoki ID:\nMisol: <code>@kanal</code> yoki <code>-1001234567890</code>\n\n⚠️ Bot kanalga admin bo'lishi shart!", parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())

@router.message(AddChannel.waiting_channel)
async def add_channel_save(message: Message, state: FSMContext):
    channel = message.text.strip()
    try:
        chat = await message.bot.get_chat(channel)
        bot_member = await message.bot.get_chat_member(chat.id, (await message.bot.get_me()).id)
        if bot_member.status not in ("administrator", "creator"):
            await message.answer("❌ Bot bu kanalda admin emas."); return
        channel_id = str(chat.id)
    except Exception as e:
        logger.warning("Kanal xato: %s", e)
        await message.answer("❌ Kanal topilmadi yoki bot admin emas."); return
    if data.channel_exists(channel_id):
        await state.clear(); await message.answer("⚠️ Bu kanal allaqachon qo'shilgan.", reply_markup=channel_kb()); return
    data.add_channel(channel_id)
    await state.clear()
    await message.answer(f"✅ Kanal qo'shildi: {chat.title}", reply_markup=channel_kb())

@router.message(F.text == "🗑 Kanal o'chirish")
async def remove_channel_start(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin", "support"):
        await message.answer("❌ Ruxsat yo'q."); return
    channels = data.get_all_channels()
    if not channels:
        await message.answer("📋 Kanallar yo'q.", reply_markup=channel_kb()); return
    await state.set_state(RemoveChannel.waiting_channel)
    await message.answer("📋 Kanallar:\n" + "\n".join(f"• <code>{ch}</code>" for ch in channels) + "\n\nKanal ID sini kiriting:", parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())

@router.message(RemoveChannel.waiting_channel)
async def remove_channel_save(message: Message, state: FSMContext):
    channel = message.text.strip()
    channel_id = channel
    if not data.channel_exists(channel_id):
        try:
            chat = await message.bot.get_chat(channel)
            channel_id = str(chat.id)
        except Exception: pass
    if not data.remove_channel(channel_id):
        await message.answer("❌ Bunday kanal topilmadi."); return
    await state.clear()
    await message.answer("✅ Kanal o'chirildi.", reply_markup=channel_kb())

@router.message(F.text == "📋 Kanallar ro'yxati")
async def list_channels(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin", "support"):
        await message.answer("❌ Ruxsat yo'q."); return
    channels = data.get_all_channels()
    if not channels:
        await message.answer("📋 Kanallar yo'q.", reply_markup=channel_kb()); return
    await message.answer("📡 Kanallar:\n" + "\n".join(f"• <code>{ch}</code>" for ch in channels), parse_mode=ParseMode.HTML, reply_markup=channel_kb())

@router.message(F.text == "📢 Reklama")
async def broadcast_start(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin", "support"):
        await message.answer("❌ Ruxsat yo'q."); return
    await state.set_state(Broadcast.waiting_message)
    await message.answer("📨 Barcha foydalanuvchilarga yuboriladigan xabarni yuboring:", reply_markup=ReplyKeyboardRemove())

@router.message(Broadcast.waiting_message)
async def broadcast_send(message: Message, state: FSMContext):
    await state.clear()
    users = data.get_all_user_ids()
    sent = failed = 0
    await message.answer(f"📤 Yuborilmoqda... ({len(users)} ta foydalanuvchi)")
    for uid in users:
        try:
            await message.bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            sent += 1
        except (TelegramForbiddenError, TelegramBadRequest): failed += 1
        except Exception as e:
            logger.warning("Xato (%d): %s", uid, e); failed += 1
    await message.answer(f"✅ Yakunlandi!\n📬 Yuborildi: {sent}\n❌ Xato: {failed}", reply_markup=admin_kb(message.from_user.id))

async def send_statistics(message):
    await message.answer(
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{data.count_users()}</b>\n"
        f"🎬 Kinolar: <b>{data.count_movies()}</b>\n"
        f"🛡 Adminlar: <b>{data.count_admins()}</b>\n"
        f"🤝 Supportlar: <b>{data.count_supports()}</b>\n"
        f"📡 Kanallar: <b>{data.count_channels()}</b>",
        parse_mode=ParseMode.HTML, reply_markup=admin_kb(message.from_user.id))

@router.message(F.text == "📊 Statistika")
async def statistics(message: Message, state: FSMContext):
    await state.clear()
    if get_role(message.from_user.id) not in ("owner", "admin", "support"):
        await message.answer("❌ Ruxsat yo'q."); return
    await send_statistics(message)

@router.message(F.text)
async def handle_movie_code(message: Message, state: FSMContext):
    if await state.get_state() is not None: return
    user_id = message.from_user.id
    channels = data.get_all_channels()
    if channels and not await check_subscriptions(message.bot, user_id):
        await send_subscribe_message(message, channels); return
    code = message.text.strip()
    movie = data.get_movie(code)
    if not movie:
        await message.answer(f"❌ <code>{code}</code> kodli kino topilmadi.", parse_mode=ParseMode.HTML); return
    try:
        if movie["type"] == "video":
            await message.answer_video(video=movie["file_id"], caption=f"🎬 Kod: <code>{code}</code>", parse_mode=ParseMode.HTML)
        else:
            await message.answer_document(document=movie["file_id"], caption=f"🎬 Kod: <code>{code}</code>", parse_mode=ParseMode.HTML)
    except TelegramBadRequest as e:
        logger.error("Xato: %s", e)
        await message.answer("❌ Kinoni yuborishda xato.")


async def main():
    data.init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    logger.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())