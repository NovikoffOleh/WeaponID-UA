import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import (
    Updater, CommandHandler, MessageHandler,
    Filters, CallbackContext, CallbackQueryHandler
)
from clip_recognizer import recognize_weapon
import os
from datetime import datetime

import os
TOKEN = os.environ.get("TOKEN")

PHOTO_PATH = "input_photos/test.jpg"
LOG_FILE = "user_logs.txt"

logging.basicConfig(level=logging.INFO)

user_langs = {}
user_locations = {}
user_last_result = {}

def get_lang(update: Update):
    user_id = update.effective_user.id
    return user_langs.get(user_id, "ua")

def log_user_data(user_id, text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] User: {user_id} — {text}\n")

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

def show_help(update: Update, context: CallbackContext):
    help_text = (
        "📖 *Інструкція з використання:*\n"
        "\n📷 Надішліть фото — розпізнаю зброю або боєприпас."
        "\n📍 /location — Надіслати місцезнаходження (координати)."
        "\n📄 /mylog — Отримати журнал знайдених об'єктів."
        "\n🌐 /lang — Змінити мову."
        "\nℹ️ /help — Показати цю інструкцію."
    )
    update.message.reply_text(help_text, parse_mode='Markdown')


def start(update: Update, context: CallbackContext):
    lang = get_lang(update)

    main_menu = ReplyKeyboardMarkup([
        ["📄 Мій журнал", "📍 Місцезнаходження"],
        ["🌐 Змінити мову", "ℹ️ Допомога"]
    ], resize_keyboard=True)

    if lang == "ua":
        update.message.reply_text(
            "👋 Надішліть фото підозрілого об’єкта (зброя або боєприпас), і я спробую його розпізнати.\n\n📷 Ви можете зробити фото або завантажити з галереї.",
            reply_markup=main_menu
        )
    else:
        update.message.reply_text(
            "👋 Send me a photo of a suspicious object (weapon or explosive), and I will try to identify it.\n\n📷 You can take a photo or upload one from your gallery.",
            reply_markup=main_menu
        )

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
    message = update.message

    if message.location:
        location = message.location
        lat = location.latitude
        lon = location.longitude

        user_id = update.effective_user.id
        coords = f"Широта: {lat}, Довгота: {lon}"
        user_locations[user_id] = coords

        if user_id in user_last_result:
            log_user_data(user_id, f"{user_last_result[user_id]} | Координати: {coords}")

        text = (
            f"📍 Ваші координати:\n{coords}\n\n⚠️ У зоні бойових дій не рекомендується автоматично передавати геолокацію. Відправте координати вручну до ДСНС. Бажаєте повернутися в меню? Введіть команду /help"
        )

        copy_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📎 Скопіювати координати", callback_data=f"copy_{lat}_{lon}")]
        ])

        update.message.reply_text(text, reply_markup=copy_markup)
    else:
        update.message.reply_text("⚠️ Повідомлення не містить геолокації.")

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data.startswith("copy_"):
        _, lat, lon = query.data.split("_")
        coords = f"{lat}, {lon}"
        query.message.reply_text(f"📌 Координати: {coords}\n(скопіюйте вручну або натисніть для перегляду на мапі)\nhttps://maps.google.com/?q={coords}")

def handle_photo(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    lang = user_langs.get(user_id, "ua")

    photo_file = update.message.photo[-1].get_file()
    photo_file.download(PHOTO_PATH)
    update.message.reply_text("🔍 Обробляю зображення, зачекайте..." if lang == "ua" else "🔍 Processing image, please wait...")

    try:
        result = recognize_weapon(PHOTO_PATH, "weapon_images", "weapons_db.json")
        user_last_result[user_id] = result.replace("\n", " | ")

        if lang == "ua":
            result += (
                "\n\n📞 Якщо ви впевнені, що це небезпечний об’єкт:\n"
                "Зателефонуйте до:\n"
                "• ДСНС: +0000000000\n"
                "• СБУ: +0000000000\n"
                "\n📍 Бажаєте визначити координати? Введіть команду /location або скористайтесь кнопкою внизу."
                "\n📍 Бажаєте повернутися в меню? Введіть команду /help"
            )
        else:
            result += (
                "\n\n📞 If you believe this object is dangerous:\n"
                "Please call:\n"
                "• Emergency Service: +0000000000\n"
                "• Security Service: +0000000000\n"
                "\n📍 Would you like to share your location? Type /location or use the button below."
            )

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
        update.message.reply_text("ℹ️ Надішліть фото або скористайтесь кнопками в меню.")

def request_location(update: Update, context: CallbackContext):
    keyboard = [[
        KeyboardButton(text="📍 Надіслати місцезнаходження", request_location=True)
    ]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("📍 Натисніть кнопку нижче, щоб поділитися місцезнаходженням. Ми лише покажемо координати, які ви зможете передати вручну:", reply_markup=reply_markup)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("lang", lang))
    dp.add_handler(CommandHandler("location", request_location))
    dp.add_handler(CommandHandler("mylog", send_user_log))
    dp.add_handler(CommandHandler("help", show_help))
    dp.add_handler(MessageHandler(Filters.regex("^(Українська 🇺🇦|English 🇬🇧)$"), set_language))
    dp.add_handler(MessageHandler(Filters.location, handle_location))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(MessageHandler(Filters.text | Filters.command | Filters.document, handle_other))
    dp.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

