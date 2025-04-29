import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, CallbackQueryHandler, ContextTypes
)
from clip_recognizer import recognize_weapon
from datetime import datetime
from asyncio import to_thread

# Константи
TOKEN = os.environ.get("TOKEN")
PHOTO_PATH = "input_photos/test.jpg"
LOG_FILE = "user_logs.txt"

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Дані користувачів
user_langs = {}
user_locations = {}
user_last_result = {}

# Функції
def get_lang(user_id):
    return user_langs.get(user_id, "ua")

def log_user_data(user_id, text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] User: {user_id} — {text}\n")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang(user_id)

    main_menu = ReplyKeyboardMarkup([
        ["📄 Мій журнал", "📍 Місцезнаходження"],
        ["🌐 Змінити мову", "ℹ️ Допомога"]
    ], resize_keyboard=True)

    text_ua = (
        "👋 Надішліть фото підозрілого об’єкта (зброя або боєприпас), і я спробую його розпізнати.\n\n"
        "📷 Ви можете зробити фото або завантажити з галереї."
    )
    text_en = (
        "👋 Send me a photo of a suspicious object (weapon or explosive), and I will try to identify it.\n\n"
        "📷 You can take a photo or upload one from your gallery."
    )

    await update.message.reply_text(text_ua if lang == "ua" else text_en, reply_markup=main_menu)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *Інструкція з використання:*\n"
        "\n📷 Надішліть фото — розпізнаю зброю або боєприпас."
        "\n📍 /location — Надіслати місцезнаходження (координати)."
        "\n📄 /mylog — Отримати журнал знайдених об'єктів."
        "\n🌐 /lang — Змінити мову."
        "\nℹ️ /help — Показати цю інструкцію."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Українська 🇺🇦", "English 🇬🇧"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("🌐 Оберіть мову / Select language:", reply_markup=reply_markup)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    choice = update.message.text

    if "Українська" in choice:
        user_langs[user_id] = "ua"
        await update.message.reply_text("✅ Мову змінено на українську.")
    elif "English" in choice:
        user_langs[user_id] = "en"
        await update.message.reply_text("✅ Language set to English.")
    else:
        await update.message.reply_text("⚠️ Невідома мова. Виберіть ще раз за допомогою /lang.")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    if message.location:
        lat = message.location.latitude
        lon = message.location.longitude
        user_locations[user_id] = f"Широта: {lat}, Довгота: {lon}"

        if user_id in user_last_result:
            log_user_data(user_id, f"{user_last_result[user_id]} | Координати: {lat},{lon}")

        coords = f"{lat}, {lon}"
        text = (
            f"📍 Ваші координати:\n{coords}\n\n⚠️ Не користуватися у зоні бойових дій!"
        )
        copy_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📎 Скопіювати координати", callback_data=f"copy_{lat}_{lon}")]
        ])
        await update.message.reply_text(text, reply_markup=copy_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("copy_"):
        _, lat, lon = query.data.split("_")
        coords = f"{lat}, {lon}"
        await query.message.reply_text(f"📌 Координати: {coords}\nhttps://maps.google.com/?q={coords}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang(user_id)

    photo_file = await update.message.photo[-1].get_file()
    os.makedirs(os.path.dirname(PHOTO_PATH), exist_ok=True)
    await photo_file.download_to_drive(PHOTO_PATH)

    text_wait = "🔍 Обробка зображення може зайняти 110с" if lang == "ua" else "🔍 Processing image..."
    await update.message.reply_text(text_wait)

        try:
        result = await to_thread(recognize_weapon, PHOTO_PATH, "weapon_images", "weapons_db.json")
        user_last_result[user_id] = result.replace("\n", " | ")

        if lang == "ua":
            result += (
                "\n\n📞 Якщо ви впевнені, що це небезпечний об’єкт:\n"
                "Зателефонуйте до:\n"
                "• ДСНС: +0000000000\n"
                "• СБУ: +0000000000\n"
                "\n📍 Бажаєте побачити координати? Введіть команду /location або скористайтесь кнопкою внизу."
                "\n📍 Бажаєте побачити меню? Введіть команду /help"
            )
        else:
            result += (
                "\n\n📞 If you believe this object is dangerous:\n"
                "Please call:\n"
                "• Emergency Service: +0000000000\n"
                "• Security Service: +0000000000\n"
                "\n📍 Would you like to share your location? Type /location or use the button below."
            )

        await update.message.reply_text(result)

        
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка розпізнавання: {e}" if lang == "ua" else f"⚠️ Recognition error: {e}")

async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📄 Мій журнал":
        await send_user_log(update, context)
    elif text == "📍 Місцезнаходження":
        await request_location(update, context)
    elif text == "🌐 Змінити мову":
        await lang(update, context)
    elif text == "ℹ️ Допомога":
        await help_command(update, context)
    else:
        await update.message.reply_text("ℹ️ Надішліть фото або скористайтесь кнопками в меню.")

async def send_user_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not os.path.exists(LOG_FILE):
        await update.message.reply_text("📂 Лог ще не створено.")
        return

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = [line for line in f if f"User: {user_id}" in line]

    if not lines:
        await update.message.reply_text("📂 У вас ще немає записів у журналі.")
        return

    user_log_path = f"user_{user_id}_log.txt"
    with open(user_log_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    with open(user_log_path, "rb") as doc:
        await update.message.reply_document(InputFile(doc), filename=f"your_log_{user_id}.txt")

    os.remove(user_log_path)

async def request_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton(text="📍 Подивитися локацію", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("📍 Натисніть кнопку нижче, щоб подтвитися локацію:", reply_markup=reply_markup)

# ⚡ Головна функція
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lang", lang))
    app.add_handler(CommandHandler("location", request_location))
    app.add_handler(CommandHandler("mylog", send_user_log))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT, handle_other))
    app.add_handler(CallbackQueryHandler(button_handler))

    logging.info("✅ Bot started successfully and polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
