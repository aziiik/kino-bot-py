import asyncio
import logging
import data  # barcha ma'lumotlar shu yerdan

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.error import TelegramError

# ─────────────────────────────────────────────
#  SOZLAMALAR — bularni o'zgartiring
# ─────────────────────────────────────────────
BOT_TOKEN = "8724276114:AAEEk6WlEtY91WJ-aaRaJlAGCFr8pAMrDEM"   # @BotFather dan oling
OWNER_ID  = 8378615092               # O'z Telegram ID'ingiz (int)
# ─────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════
#  ROL TEKSHIRISH
# ══════════════════════════════════════════════
def is_owner(uid: int) -> bool:
    return uid == OWNER_ID

def is_admin(uid: int) -> bool:
    return uid == OWNER_ID or uid in data.admins

def is_support(uid: int) -> bool:
    return uid == OWNER_ID or uid in data.admins or uid in data.supports


# ══════════════════════════════════════════════
#  FOYDALANUVCHI RO'YXATGA OLISH
# ══════════════════════════════════════════════
def register_user(uid: int, username: str = ""):
    key = str(uid)
    if key not in data.users:
        data.users[key] = {"username": username}


# ══════════════════════════════════════════════
#  MAJBURIY OBUNA
# ══════════════════════════════════════════════
async def check_subscription(bot, uid: int) -> list:
    """Obuna bo'lmagan kanallar ro'yxatini qaytaradi."""
    not_joined = []
    for ch in data.channels:
        try:
            member = await bot.get_chat_member(ch, uid)
            if member.status in ("left", "kicked"):
                not_joined.append(ch)
        except TelegramError:
            not_joined.append(ch)
    return not_joined

def sub_keyboard(channels: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.lstrip('@')}")]
        for ch in channels
    ]
    buttons.append([InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)


# ══════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username or "")

    # Deep link orqali kelgan kod
    if ctx.args:
        ctx.user_data["pending_code"] = ctx.args[0]

    not_joined = await check_subscription(ctx.bot, user.id)
    if not_joined:
        await update.message.reply_text(
            "🎬 <b>KinoHour</b> botiga xush kelibsiz!\n\n"
            "📢 Kinolarni olish uchun quyidagi kanallarga obuna bo'ling:",
            parse_mode="HTML",
            reply_markup=sub_keyboard(not_joined)
        )
        return

    pending = ctx.user_data.pop("pending_code", None)
    if pending:
        await send_movie(update, ctx, pending)
        return

    await update.message.reply_text(
        "🎬 <b>KinoHour</b> botiga xush kelibsiz!\n\n"
        "Kino kodini yuboring — kino darhol yuboriladi.\n"
        "Misol: <code>001</code>",
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════
#  OBUNA TEKSHIRISH CALLBACK
# ══════════════════════════════════════════════
async def cb_check_sub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    not_joined = await check_subscription(ctx.bot, user.id)
    if not_joined:
        await query.message.edit_reply_markup(reply_markup=sub_keyboard(not_joined))
        await query.answer("❌ Hali ham obuna bo'lmadingiz!", show_alert=True)
        return

    pending = ctx.user_data.pop("pending_code", None)
    await query.message.delete()

    if pending:
        await ctx.bot.send_message(user.id, "✅ Obuna tasdiqlandi! Kino yuborilmoqda...")
        movie = data.movies.get(pending)
        if movie:
            await ctx.bot.send_document(
                user.id, movie["file_id"],
                caption=f"🎬 <b>{movie.get('title', pending)}</b>",
                parse_mode="HTML"
            )
        else:
            await ctx.bot.send_message(user.id, "❌ Bunday kodli kino topilmadi.")
    else:
        await ctx.bot.send_message(
            user.id,
            "✅ Obuna tasdiqlandi!\nEndi kino kodini yuboring.",
            parse_mode="HTML"
        )


# ══════════════════════════════════════════════
#  KINO YUBORISH
# ══════════════════════════════════════════════
async def send_movie(update: Update, ctx: ContextTypes.DEFAULT_TYPE, code: str):
    movie = data.movies.get(code)
    if not movie:
        await update.message.reply_text("❌ Bunday kodli kino topilmadi. Kodni tekshiring.")
        return
    caption = f"🎬 <b>{movie.get('title', code)}</b>"
    if movie.get("desc"):
        caption += f"\n\n{movie['desc']}"
    try:
        await update.message.reply_document(movie["file_id"], caption=caption, parse_mode="HTML")
    except TelegramError as e:
        log.error(f"Kino yuborishda xato: {e}")
        await update.message.reply_text("⚠️ Kino yuborishda xatolik. Admin bilan bog'laning.")


# ══════════════════════════════════════════════
#  MATN HANDLER
# ══════════════════════════════════════════════
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()
    state = ctx.user_data.get("state")

    # Admin holati
    if state and is_support(user.id):
        await handle_admin_state(update, ctx, state, text)
        return

    # Oddiy foydalanuvchi — kod yubordi
    register_user(user.id, user.username or "")
    not_joined = await check_subscription(ctx.bot, user.id)
    if not_joined:
        ctx.user_data["pending_code"] = text
        await update.message.reply_text(
            "📢 Avval kanallarga obuna bo'ling:",
            reply_markup=sub_keyboard(not_joined)
        )
        return

    await send_movie(update, ctx, text)


# ══════════════════════════════════════════════
#  FAYL HANDLER — kino qo'shish
# ══════════════════════════════════════════════
async def handle_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_support(user.id):
        return

    state = ctx.user_data.get("state", "")
    if not state.startswith("add_movie_wait_file:"):
        await update.message.reply_text("Avval /panel → ➕ Kino qo'shish tugmasini bosing.")
        return

    code   = state.split(":", 1)[1]
    msg    = update.message
    file_id = None

    if msg.document:
        file_id = msg.document.file_id
    elif msg.video:
        file_id = msg.video.file_id

    if not file_id:
        await update.message.reply_text("❌ Video yoki document yuboring.")
        return

    title = ctx.user_data.pop("movie_title", code)
    data.movies[code] = {"file_id": file_id, "title": title, "desc": ""}
    ctx.user_data["state"] = None

    await update.message.reply_text(
        f"✅ Kino qo'shildi!\n"
        f"📌 Kod: <code>{code}</code>\n"
        f"🎬 Nom: {title}",
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════
#  ADMIN PANEL
# ══════════════════════════════════════════════
def admin_keyboard(uid: int) -> InlineKeyboardMarkup:
    rows = [
        ["➕ Kino qo'shish", "🗑 Kino o'chirish"],
        ["📢 Reklama",        "📊 Statistika"],
        ["📡 Kanal qo'shish", "❌ Kanal o'chirish", "📋 Kanallar"],
    ]
    if is_admin(uid):
        rows.append(["🤝 Support qo'shish", "🚷 Support o'chirish"])
    if is_owner(uid):
        rows.append(["👑 Admin qo'shish", "🚫 Admin o'chirish"])
    rows.append(["🔙 Yopish"])
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t, callback_data=f"panel:{t}") for t in row] for row in rows]
    )

async def cmd_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_support(update.effective_user.id):
        await update.message.reply_text("❌ Sizda ruxsat yo'q.")
        return
    await update.message.reply_text(
        "🛡 <b>Admin Panel</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(update.effective_user.id)
    )

async def cb_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]

    class FakeUpdate:
        effective_user = query.from_user
        message        = query.message

    await admin_menu_action(FakeUpdate(), ctx, action)


async def admin_menu_action(update, ctx, action: str):
    uid = update.effective_user.id
    msg = update.message

    if action == "➕ Kino qo'shish":
        ctx.user_data["state"] = "add_movie_wait_code"
        await msg.reply_text("🎬 Kino kodini kiriting (masalan: <code>001</code>):", parse_mode="HTML")

    elif action == "🗑 Kino o'chirish":
        ctx.user_data["state"] = "del_movie"
        kinolar = "\n".join([f"<code>{k}</code> — {v['title']}" for k, v in data.movies.items()]) or "— Hozircha yo'q"
        await msg.reply_text(f"🗑 O'chirmoqchi bo'lgan kino kodini yuboring:\n\n{kinolar}", parse_mode="HTML")

    elif action == "📢 Reklama":
        if not is_admin(uid):
            await msg.reply_text("❌ Ruxsat yo'q.")
            return
        ctx.user_data["state"] = "broadcast"
        await msg.reply_text("📢 Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:\n(HTML format qo'llab-quvvatlanadi)")

    elif action == "📡 Kanal qo'shish":
        ctx.user_data["state"] = "add_channel"
        await msg.reply_text("📡 Kanal username'ini kiriting:\nMisol: <code>@mening_kanalim</code>", parse_mode="HTML")

    elif action == "❌ Kanal o'chirish":
        ctx.user_data["state"] = "del_channel"
        ch_list = "\n".join(data.channels) or "— Hozircha yo'q"
        await msg.reply_text(f"❌ O'chirmoqchi bo'lgan kanalning username'ini yuboring:\n\n{ch_list}")

    elif action == "📋 Kanallar":
        ch_list = "\n".join(data.channels) if data.channels else "— Hozircha yo'q"
        await msg.reply_text(f"📋 <b>Majburiy obuna kanallari:</b>\n{ch_list}", parse_mode="HTML")

    elif action == "👑 Admin qo'shish" and is_owner(uid):
        ctx.user_data["state"] = "add_admin"
        await msg.reply_text("👑 Yangi admin Telegram ID'ini kiriting:")

    elif action == "🚫 Admin o'chirish" and is_owner(uid):
        ctx.user_data["state"] = "del_admin"
        admins_list = "\n".join(str(a) for a in data.admins) or "— Hozircha yo'q"
        await msg.reply_text(f"🚫 O'chirmoqchi bo'lgan admin ID'ini kiriting:\n\n{admins_list}")

    elif action == "🤝 Support qo'shish" and is_admin(uid):
        ctx.user_data["state"] = "add_support"
        await msg.reply_text("🤝 Yangi support Telegram ID'ini kiriting:")

    elif action == "🚷 Support o'chirish" and is_admin(uid):
        ctx.user_data["state"] = "del_support"
        sup_list = "\n".join(str(s) for s in data.supports) or "— Hozircha yo'q"
        await msg.reply_text(f"🚷 O'chirmoqchi bo'lgan support ID'ini kiriting:\n\n{sup_list}")

    elif action == "📊 Statistika":
        await stats_message(msg)

    elif action == "🔙 Yopish":
        ctx.user_data["state"] = None
        await msg.reply_text("✅ Panel yopildi.")

    else:
        await msg.reply_text("❌ Ruxsat yo'q.")


# ══════════════════════════════════════════════
#  ADMIN HOLAT HANDLER
# ══════════════════════════════════════════════
async def handle_admin_state(update: Update, ctx: ContextTypes.DEFAULT_TYPE, state: str, text: str):
    msg = update.message

    if state == "add_movie_wait_code":
        ctx.user_data["state"]      = f"add_movie_wait_title:{text}"
        ctx.user_data["movie_code"] = text
        await msg.reply_text(
            f"✅ Kod: <code>{text}</code>\nEndi kino nomini kiriting:",
            parse_mode="HTML"
        )

    elif state.startswith("add_movie_wait_title:"):
        code = state.split(":", 1)[1]
        ctx.user_data["movie_title"] = text
        ctx.user_data["state"]       = f"add_movie_wait_file:{code}"
        await msg.reply_text("✅ Nom saqlandi.\nEndi kino faylini (video yoki document) yuboring:")

    elif state == "del_movie":
        ctx.user_data["state"] = None
        if text in data.movies:
            title = data.movies[text]["title"]
            del data.movies[text]
            await msg.reply_text(f"✅ <b>{title}</b> (<code>{text}</code>) o'chirildi.", parse_mode="HTML")
        else:
            await msg.reply_text("❌ Bunday kodli kino topilmadi.")

    elif state == "broadcast":
        ctx.user_data["state"] = None
        users = list(data.users.keys())
        await msg.reply_text(f"📢 {len(users)} ta foydalanuvchiga yuborilmoqda...")
        sent = failed = 0
        for uid in users:
            try:
                await ctx.bot.send_message(int(uid), text, parse_mode="HTML")
                sent += 1
            except TelegramError:
                failed += 1
            await asyncio.sleep(0.05)
        await msg.reply_text(f"✅ Yuborildi: <b>{sent}</b>\n❌ Xato: <b>{failed}</b>", parse_mode="HTML")

    elif state == "add_channel":
        ctx.user_data["state"] = None
        ch = text if text.startswith("@") else f"@{text}"
        if ch not in data.channels:
            data.channels.append(ch)
            await msg.reply_text(f"✅ {ch} majburiy obunaga qo'shildi.")
        else:
            await msg.reply_text("ℹ️ Bu kanal allaqachon mavjud.")

    elif state == "del_channel":
        ctx.user_data["state"] = None
        ch = text if text.startswith("@") else f"@{text}"
        if ch in data.channels:
            data.channels.remove(ch)
            await msg.reply_text(f"✅ {ch} o'chirildi.")
        else:
            await msg.reply_text("❌ Bunday kanal topilmadi.")

    elif state == "add_admin":
        ctx.user_data["state"] = None
        try:
            aid = int(text)
            if aid not in data.admins:
                data.admins.append(aid)
                await msg.reply_text(f"✅ <code>{aid}</code> admin qilindi.", parse_mode="HTML")
            else:
                await msg.reply_text("ℹ️ Bu foydalanuvchi allaqachon admin.")
        except ValueError:
            await msg.reply_text("❌ ID raqam bo'lishi kerak.")

    elif state == "del_admin":
        ctx.user_data["state"] = None
        try:
            aid = int(text)
            if aid in data.admins:
                data.admins.remove(aid)
                await msg.reply_text(f"✅ <code>{aid}</code> admin ro'yxatidan o'chirildi.", parse_mode="HTML")
            else:
                await msg.reply_text("❌ Bu foydalanuvchi admin emas.")
        except ValueError:
            await msg.reply_text("❌ ID raqam bo'lishi kerak.")

    elif state == "add_support":
        ctx.user_data["state"] = None
        try:
            sid = int(text)
            if sid not in data.supports:
                data.supports.append(sid)
                await msg.reply_text(f"✅ <code>{sid}</code> support qilindi.", parse_mode="HTML")
            else:
                await msg.reply_text("ℹ️ Bu foydalanuvchi allaqachon support.")
        except ValueError:
            await msg.reply_text("❌ ID raqam bo'lishi kerak.")

    elif state == "del_support":
        ctx.user_data["state"] = None
        try:
            sid = int(text)
            if sid in data.supports:
                data.supports.remove(sid)
                await msg.reply_text(f"✅ <code>{sid}</code> support ro'yxatidan o'chirildi.", parse_mode="HTML")
            else:
                await msg.reply_text("❌ Bu foydalanuvchi support emas.")
        except ValueError:
            await msg.reply_text("❌ ID raqam bo'lishi kerak.")

    else:
        ctx.user_data["state"] = None


# ══════════════════════════════════════════════
#  STATISTIKA
# ══════════════════════════════════════════════
async def stats_message(msg):
    await msg.reply_text(
        "📊 <b>Statistika</b>\n\n"
        f"👤 Foydalanuvchilar: <b>{len(data.users)}</b>\n"
        f"🎬 Kinolar: <b>{len(data.movies)}</b>\n"
        f"👑 Adminlar: <b>{len(data.admins)}</b>\n"
        f"🤝 Supportlar: <b>{len(data.supports)}</b>\n"
        f"📡 Kanallar: <b>{len(data.channels)}</b>",
        parse_mode="HTML"
    )

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_support(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return
    await stats_message(update.message)


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("panel", cmd_panel))
    app.add_handler(CommandHandler("stats", cmd_stats))

    app.add_handler(CallbackQueryHandler(cb_check_sub, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(cb_panel,     pattern="^panel:"))

    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("✅ KinoHour bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
