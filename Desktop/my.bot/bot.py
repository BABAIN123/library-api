import json
import logging
import os
import random
from dotenv import load_dotenv
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# 1. ЗАГРУЗКА ОКРУЖЕНИЯ И ТОКЕНА
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Состояния для диалога опроса профиля
NAME, COLOR = range(2)

# Глобальный словарь для хранения данных пользователей
user_data = {}

# Список шуток
JOKES = [
    "Почему программисты путают Хэллоуин и Рождество? Потому что Oct 31 == Dec 25!",
    "В мире есть 10 типов людей: те, кто понимают двоичную систему, и те, кто нет.",
    "Программист ставит два стакана на тумбочку перед сном: один с водой — если захочет пить, второй пустой — если не захочет.",
]


# 2. РАБОТА С JSON (БАЗА ДАННЫХ)
def load_data():
    """Загрузка данных из файла user.json при старте бота"""
    global user_data
    if os.path.exists("user.json"):
        with open("user.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            # Преобразуем строковые ключи JSON обратно в int (user_id)
            user_data = {int(k): v for k, v in data.items()}
    else:
        user_data = {}


def save_data():
    """Сохранение текущего состояния user_data в файл user.json"""
    with open("user.json", "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)


# 3. КЛАВИАТУРА И ОСНОВНЫЕ КОМАНДЫ
def get_main_keyboard():
    """Генерация главного меню"""
    keyboard = [
        [KeyboardButton("О боте")],
        [KeyboardButton("Шутка")],
        [KeyboardButton("Автор")],
        [KeyboardButton("Заполнить профиль")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Выберите нужную команду на клавиатуре ниже или введите /profile для просмотра профиля:",
        reply_markup=get_main_keyboard(),
    )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ сохранённого профиля (/profile)"""
    user_id = update.effective_user.id
    profile_info = user_data.get(user_id)

    if profile_info:
        name = profile_info.get("name", "Не указано")
        color = profile_info.get("color", "Не указан")
        text = f"👤 Ваш профиль:\n• Имя: {name}\n• Любимый цвет: {color}"
    else:
        text = "Ваш профиль пока пуст. Нажмите кнопку «Заполнить профиль», чтобы ввести данные!"

    await update.message.reply_text(text)


# 4. СЦЕНАРИЙ ОПРОСА (КОНВЕРСАЦИЯ)
async def set_profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Старт опроса"""
    await update.message.reply_text(
        "Давайте зафиксируем ваши данные.\nКак вас зовут?\n\n(Для отмены введите /cancel)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение имени"""
    context.user_data["temp_name"] = update.message.text
    await update.message.reply_text("Отлично! Какой ваш любимый цвет?")
    return COLOR


async def get_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение цвета, запись в словарь и сохранение в JSON"""
    user_id = update.effective_user.id
    color = update.message.text
    name = context.user_data.get("temp_name", "Неизвестно")

    # Сохраняем локально и в файл
    user_data[user_id] = {"name": name, "color": color}
    save_data()

    await update.message.reply_text(
        f"Спасибо! Профиль сохранён:\n• Имя: {name}\n• Цвет: {color}",
        reply_markup=get_main_keyboard(),
    )
    return ConversationHandler.END


async def cancel_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Прерывание опроса"""
    await update.message.reply_text(
        "Заполнение профиля отменено.", reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


# 5. ОБРАБОТКА ОБЫЧНЫХ СООБЩЕНИЙ С КЛАВИАТУРЫ
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text

    if user_text == "О боте":
        text = "🤖 Этот бот умеет сохранять данные профиля в JSON-файл!"
    elif user_text == "Шутка":
        text = f"😂 {random.choice(JOKES)}"
    elif user_text == "Автор":
        text = "✍️ Автор этого бота — прекрасный разработчик!"
    else:
        text = "Не понял команду 🤷"

    await update.message.reply_text(text)


# 6. ЗАПУСК БОТА
def main() -> None:
    # Загружаем JSON базу при старте приложения
    load_data()

    # Проверка, что токен был успешно считан из .env
    if not TOKEN:
        raise ValueError("Ошибка: Токен BOT_TOKEN не найден в переменной окружения или .env файле!")

    application = Application.builder().token(TOKEN).build()

    # Сборка обработчика диалогов профиля
    profile_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^Заполнить профиль$"), set_profile_start)
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_color)],
        },
        fallbacks=[CommandHandler("cancel", cancel_profile)],
    )

    # Регистрация всех хэндлеров (строго в правильном порядке)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(profile_handler)
    
    # Текст обрабатываем в самом конце, чтобы не перебивать диалоги
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Запуск polling
    application.run_polling()


if __name__ == "__main__":
    main()