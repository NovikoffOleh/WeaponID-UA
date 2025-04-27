import logging
import os
import time
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
)
from telegram import Bot
from clip_recognizer import recognize_weapon

# 1. Налаштування
TOKEN = os.environ.get("TOKEN")
PHOTO_PATH = "input_photos/test.jpg"
LOG_FILE = "user_logs.txt"

# Переконаємося що папка для фото існує
os.makedirs(os.path.dirname(PHOTO_PATH), exist_ok=True)

# 2. Налаштування логування
logging.basicConfig(level=logging.INFO)

user_langs = {}
user_locations = {}
user_last_result = {}

# 3. Хелпер-функції
def get_lang(update: Update):
    user_id = update.effective_user.id
    return user_langs.get(user_id, "ua")

def log_user_data(user_id, text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] User: {user_id} — {text}\n")

# 4. Хендлери команд
def start(update: Update, context: CallbackContext):
    lang = get_lang(update)
    main_menu = ReplyKeyboardMarkup([
        ["📄 Мій журнал", "📍 Місцезнаходження"],
        ["🌐 Змінити мову", "ℹ️ Допомога"]
    ], resize_keyboard=True)

    text = (
        "👋 Надішліть фото підозрілого об’єкта (зброя або боєприпас)."
        if lang == "ua"
        else
        "👋 Send me a photo of a suspicious object (weapon or explosive)."
    )
    update.message.reply_text(text, reply_markup=main_menu)

def show_help(update: Update, context: CallbackContext):
    help_text = (
        "📖 *Інструкція:*\n"
        "📷 Надішліть фото для розпізнавання.\n"
        "📍 /location — Надіслати місцезнаходження.\n"
        "📄 /mylog — Ваш журнал знахідок.\n"
        "🌐 /lang — Змінити мову.\n"
        "ℹ️ /help — Допомога."
    )
    update.message.reply_text(help_text, parse_mode='Markdown')

def lang(update: Update, context: CallbackContext):
    keyboard = [["Українська 🇺🇦", "English 🇬🇧"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("🌐 Оберіть мову / Select language:", reply_markup=reply_markup)

def set_language(update: Update, context: CallbackContext):
    choice = update.message.text
    user_id = update.effective_user.id

    if "Українська" in choice:
        user_langs[user_id] = "ua"
        update.message.reply_text("✅ Мову змінено на українську.")
    elif "English" in choice:
        user_langs[user_id] = "en"
        update.message.reply_text("✅ Language set to English.")
    else:
        update.message.reply_text("⚠️ Невідома мова. Виберіть ще раз за допомогою /lang.")

def handle_location(update: Update, context: CallbackContext):
    if update.message.location:
        location = update.message.location
        coords = f"Широта: {location.latitude}, Довгота: {location.longitude}"

        user_id = update.effective_user.id
        user_locations[user_id] = coords
        if user_id in user_last_result:
            log_user_data(user_id, f"{user_last_result[user_id]} | Координати: {coords}")

        text = (
            f"📍 Ваші координати:\n{coords}\n\n⚠️ Якщо перебуваєте у зоні бойових дій — передавайте координати вручну відповідним службам."
        )
        update.message.reply_text(text)
    else:
        update.message.reply_text("⚠️ Немає даних про місцезнаходження.")

def send_user_log(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not os.path.exists(LOG_FILE):
        update.message.reply_text("📂 Лог ще не створено.")
        return

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = [line for line in f if f"User: {user_id}" in line]

    if not lines:
        update.message.reply_text("📂 У вас ще немає записів у журналі.")
        return

    user_log_path = f"user_{user_id}_log.txt"
    with open(user_log_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    with open(user_log_path, "rb") as doc:
        update.message.reply_document(InputFile(doc), filename=f"your_log_{user_id}.txt")

    os.remove(user_log_path)

def request_location(update: Update, context: CallbackContext):
    keyboard = [[
        KeyboardButton(text="📍 Надіслати місцезнаходження", request_location=True)
    ]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("📍 Надішліть координати:", reply_markup=reply_markup)

def handle_photo(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    lang = user_langs.get(user_id, "ua")

    photo_file = update.message.photo[-1].get_file()
    photo_file.download(PHOTO_PATH)
    update.message.reply_text("🔍 Обробляю зображення..." if lang == "ua" else "🔍 Processing image...")

    try:
        result = recognize_weapon(PHOTO_PATH, "weapon_images", "weapons_db.json")
        user_last_result[user_id] = result.replace("\n", " | ")
        update.message.reply_text(result)
    except Exception as e:
        update.message.reply_text(f"⚠️ Помилка розпізнавання: {e}" if lang == "ua" else f"⚠️ Recognition error: {e}")

def handle_other(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "📄 Мій журнал":
        send_user_log(update, context)
    elif text == "📍 Місцезнаходження":
        request_location(update, context)
    elif text == "🌐 Змінити мову":
        lang(update, context)
    elif text == "ℹ️ Допомога":
        show_help(update, context)
    else:
        update.message.reply_text("ℹ️ Надішліть фото або скористайтесь меню.")

# 5. Основна функція
def main():
    bot = Bot(TOKEN)
    dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", show_help))
    dispatcher.add_handler(CommandHandler("lang", lang))
    dispatcher.add_handler(CommandHandler("location", request_location))
    dispatcher.add_handler(CommandHandler("mylog", send_user_log))
    dispatcher.add_handler(MessageHandler(Filters.regex("^(Українська 🇺🇦|English 🇬🇧)$"), set_language))
    dispatcher.add_handler(MessageHandler(Filters.location, handle_location))
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_photo))
    dispatcher.add_handler(MessageHandler(Filters.text | Filters.command | Filters.document, handle_other))

    logging.info("✅ Бот запущений успішно!")

    while True:
        time.sleep(10)

if __name__ == '__main__':
    main()
