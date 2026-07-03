"""
СнекМаркет — Telegram Bot
Принимает заказы из Mini App и отправляет менеджеру
"""

import json
import logging
import os
from datetime import datetime

from telegram import (
    Update,
    WebAppInfo,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ─── Настройки ────────────────────────────────────────────────────────────────

BOT_TOKEN   = os.getenv("BOT_TOKEN", "ВСТАВЬ_ТОКЕН_СЮДА")
MANAGER_ID  = int(os.getenv("MANAGER_ID", "0"))   # твой Telegram user_id
MINIAPP_URL = os.getenv("MINIAPP_URL", "https://ТВОЙ_САЙТ/shop")

# ─── Логирование ──────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ─── /start ───────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("🛒 Открыть магазин", web_app=WebAppInfo(url=MINIAPP_URL))]],
        resize_keyboard=True,
    )
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Добро пожаловать в *СнекМаркет* — оптовые снеки для пивных магазинов.\n\n"
        "Нажмите кнопку ниже, чтобы открыть каталог и оформить заказ:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )

# ─── Приём заказа из Mini App ─────────────────────────────────────────────────

async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Срабатывает когда Mini App отправляет данные через tg.sendData()"""
    try:
        raw  = update.effective_message.web_app_data.data
        data = json.loads(raw)
    except Exception as e:
        log.error(f"Ошибка парсинга данных: {e}")
        await update.message.reply_text("Что-то пошло не так при оформлении заказа. Позвоните нам.")
        return

    user    = update.effective_user
    now     = datetime.now().strftime("%d.%m.%Y %H:%M")
    shop    = data.get("shop", "—")
    name    = data.get("name", "—")
    phone   = data.get("phone", "—")
    addr    = data.get("addr", "—")
    comment = data.get("comment", "")
    total   = data.get("total", 0)
    items   = data.get("items", [])

    # ── Формируем строки товаров ──────────────────────────────────────────────
    items_text = ""
    for it in items:
        item_name  = it.get("name", "—")
        qty        = it.get("qty", 0)
        price      = it.get("price", 0)
        subtotal   = round(price * qty)
        items_text += f"  • {item_name}\n    {qty} × {price:,} ₽ = {subtotal:,} ₽\n"

    # ── Сообщение менеджеру ───────────────────────────────────────────────────
    manager_msg = (
        f"🛒 *НОВЫЙ ЗАКАЗ* #{user.id}\n"
        f"🕐 {now}\n"
        f"──────────────────────\n"
        f"🏪 *Магазин:* {shop}\n"
        f"👤 *Контакт:* {name}\n"
        f"📞 *Телефон:* {phone}\n"
        f"📍 *Адрес:* {addr}\n"
        + (f"💬 *Комментарий:* {comment}\n" if comment else "")
        + f"──────────────────────\n"
        f"📦 *Состав заказа:*\n"
        f"{items_text}"
        f"──────────────────────\n"
        f"💰 *ИТОГО: {total:,} ₽*\n"
        f"──────────────────────\n"
        f"👤 Telegram: @{user.username or '—'} (id: {user.id})"
    )

    # ── Кнопки менеджера: позвонить ───────────────────────────────────────────
    manager_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("💬 Написать", url=f"tg://user?id={user.id}"),
    ]])

    # ── Отправляем менеджеру ──────────────────────────────────────────────────
    if MANAGER_ID:
        try:
            await ctx.bot.send_message(
                chat_id=MANAGER_ID,
                text=manager_msg,
                parse_mode="Markdown",
                reply_markup=manager_kb,
            )
            log.info(f"Заказ от {user.id} отправлен менеджеру {MANAGER_ID}")
        except Exception as e:
            log.error(f"Не удалось отправить менеджеру: {e}")
    else:
        log.warning("MANAGER_ID не задан — заказ не отправлен менеджеру")

    # ── Подтверждение клиенту ─────────────────────────────────────────────────
    await update.message.reply_text(
        f"✅ *Заказ принят!*\n\n"
        f"Магазин: {shop}\n"
        f"Сумма: *{total:,} ₽*\n\n"
        f"Менеджер свяжется с вами по номеру {phone} в течение 30 минут для подтверждения и уточнения времени доставки.",
        parse_mode="Markdown",
    )

# ─── /help ────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛒 *СнекМаркет — оптовые снеки*\n\n"
        "Доставка снеков и закусок в пивные магазины\n"
        "по Москве и Московской области.\n\n"
        "📦 График доставки: вторник и пятница\n"
        "📞 По вопросам: напишите нам\n\n"
        "Нажмите /start чтобы открыть каталог",
        parse_mode="Markdown",
    )

# ─── Запуск ───────────────────────────────────────────────────────────────────

def main():
    if BOT_TOKEN == "ВСТАВЬ_ТОКЕН_СЮДА":
        print("❌ Укажи BOT_TOKEN в переменных окружения или прямо в коде")
        return
    if MANAGER_ID == 0:
        print("⚠️  MANAGER_ID не указан — заказы не будут приходить менеджеру")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    print("✅ Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
