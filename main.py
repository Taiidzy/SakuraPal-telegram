import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from service.api import Anime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Логирование в консоль
    ]
)
logger = logging.getLogger(__name__)

# Хранилище для состояния пользователя
user_states = {}

# Функция обработки команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.message.from_user.id} начал взаимодействие с ботом.")
    keyboard = [
        [InlineKeyboardButton("Поиск", callback_data="search")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать! Выбери вариант ниже:", reply_markup=reply_markup)

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    logger.info(f"Пользователь {query.from_user.id} нажал кнопку: {query.data}")

    if query.data == "home":
        keyboard = [
            [InlineKeyboardButton("Поиск", callback_data="search")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Добро пожаловать! Выбери вариант ниже:", reply_markup=reply_markup)

    elif query.data == "search":
        user_states[query.from_user.id] = "waiting_for_search"
        await query.edit_message_text("Введите текст для поиска:")

    elif query.data == "go_back_search":
        user_states[query.from_user.id] = "waiting_for_search"
        
        # Удаляем предыдущее сообщение (если оно было изображением)
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Ошибка при удалении сообщения: {e}")

        await query.message.reply_text("Введите текст для поиска:")

    elif query.data.startswith("animeID_"):
        anime_id = query.data.split("_")[1]
        logger.info(f"Пользователь {query.from_user.id} запросил информацию об аниме с ID: {anime_id}")
        title = await Anime.get_title(anime_id)
        if not title:  # Проверка на случай пустого ответа
            logger.error(f"Ошибка получения данных об аниме для ID: {anime_id}")
            await query.edit_message_text("Ошибка получения данных об аниме.")
            return

        image_url = f"https://static-libria.weekstorm.one{title[0]['poster']}"
        text = f"Название:\n<b>{title[0]['title_name']}</b>\nОписание:\n{title[0]['description']}\nЖанры: {title[0]['genres']}"
        keyboard = [
            [InlineKeyboardButton("Назад", callback_data="go_back_search")],
            [InlineKeyboardButton("Скачать", callback_data=f"download_{title[0]['title_id']}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            response = requests.get(image_url, stream=True)  # stream=True для больших файлов
            response.raise_for_status()  # Проверка на ошибки HTTP (4xx или 5xx)

            # Отправка фото как InputMediaPhoto
            media = InputMediaPhoto(media=response.raw, caption=text, parse_mode=ParseMode.HTML)
            await query.edit_message_media(media=media, reply_markup=reply_markup)

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при скачивании изображения: {e}")
            await query.edit_message_text(f"Ошибка при загрузке изображения: {e}")  # Сообщение об ошибке в чат
        except Exception as e:
            logger.error(f"Непредвиденная ошибка: {e}")
            await query.edit_message_text(f"Непредвиденная ошибка при обработке: {e}")

    elif query.data.startswith("download_"):
        anime_id = query.data.split("_")[1]
        logger.info(f"Пользователь {query.from_user.id} запросил скачивание аниме с ID: {anime_id}")
        torrents_list = await Anime.get_torrent(anime_id)
        if not torrents_list:  # Проверка на случай пустого ответа
            logger.error(f"Ошибка получения данных о торренте для аниме с ID: {anime_id}")
            await query.edit_message_text("Ошибка получения данных о торренте.")
            return

        keyboard = [
            [InlineKeyboardButton(f"{torrent['quality']} Размер: {torrent['size']}", callback_data=f"animeDownload")]
            for torrent in torrents_list
        ]
        keyboard.append([InlineKeyboardButton("Назад", callback_data="go_back_search")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        logger.info(keyboard)
        await query.message.delete()
        await query.message.reply_text("Выберите качество:", reply_markup=reply_markup)

# Обработка текстового ввода
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    logger.info(f"Пользователь {user_id} ввел текст: {update.message.text}")

    # Проверяем, ожидает ли пользователь ввода текста для поиска
    if user_states.get(user_id) == "waiting_for_search":
        user_query = update.message.text
        try:
            anime_list = await Anime.search(user_query)
        except Exception as e:
            anime_list = None  # Если произошла ошибка, обрабатываем как пустой результат
            logger.error(f"Ошибка при поиске аниме: {e}")  # Логируем ошибку для отладки

        user_states[user_id] = None  # Сбрасываем состояние пользователя

        # Формируем кнопки с результатами поиска или ошибкой
        if anime_list:
            keyboard = [
                [InlineKeyboardButton(anime["name"], callback_data=f"animeID_{anime['id']}")]
                for anime in anime_list
            ]
            keyboard.append([InlineKeyboardButton("Назад", callback_data="go_back_search")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Найденные аниме:", reply_markup=reply_markup)
        else:
            keyboard = [[InlineKeyboardButton("Назад", callback_data="go_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Ничего не найдено. Попробуйте другой запрос.", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Нажмите 'Поиск', чтобы начать поиск.")

# Основной блок
if __name__ == '__main__':
    logger.info("Запуск бота...")
    # Замени 'YOUR_TOKEN' на токен от BotFather
    app = ApplicationBuilder().token("7648087080:AAGWbigCK_I9aR4mfdfCw4IqDMweshM2vww").build()

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Бот запущен!")
    app.run_polling()