import os
import time
import logging
import qbittorrentapi
from telegram import InputMediaDocument

QB_HOST = "localhost"
QB_PORT = 8080
QB_USERNAME = "admin"
QB_PASSWORD = "adminadmin"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Логирование в консоль
    ]
)
logger = logging.getLogger(__name__)

qb = qbittorrentapi.Client(
        host=QB_HOST,
        port=QB_PORT,
        username=QB_USERNAME,
        password=QB_PASSWORD
    )

class Downloader:
    async def connect():
        try:
            qb.auth_log_in()
            logger.info("Подключено к qBittorrent")
            return "✅ Успешно подключено к qBittorrent"
        except qbittorrentapi.LoginFailed as e:
            exit()
            logger.error(f"Ошибка авторизации: {e}")
            return f"❌ Ошибка авторизации: {e}"
        
    async def start(magnet, magnet_hash, user_id, update):
        query = update.callback_query
        await query.answer()
        # Добавляем торрент в загрузку
        qb.torrents_add(urls=magnet)
        logger.info(f"Начата загрузка для магнит-ссылки: {magnet}")
        
        # Добавляем небольшую задержку перед попыткой получения информации о торренте
        time.sleep(5)

        # Получаем информацию о торренте
        torrents_info = qb.torrents_info(hash=magnet_hash)
        torrent = next((t for t in torrents_info if t.hash == magnet_hash), None)

        if not torrent:
            logger.error(f"Не удалось найти торрент по ссылке: {magnet}")
            await update.reply_text("Не удалось найти торрент.")
            return
        
        # Следим за прогрессом
        while torrent.state != "seeding":  # Пока торрент не завершит загрузку
            torrents = qb.torrents_info()
            torrent = next((t for t in torrents if t.hash == magnet_hash), None)
            progress = torrent.progress * 100
            logger.info(f"Прогресс загрузки: {progress}%")

            # Обновляем сообщение с прогрессом
            await query.edit_message_text(f"Загрузка: {progress:.2f}%")
            time.sleep(5)  # Проверяем прогресс каждые 5 секунд

        # Загрузка завершена, отправляем файлы по порядку
        await Downloader.send_files(user_id, update, torrent)


    @staticmethod
    async def send_files(user_id, update, torrent):
        # Получаем список файлов в торренте
        files = qb.torrents_files(torrent.hash)
        sorted_files = sorted(files, key=lambda f: f.name)  # Сортируем файлы по имени

        # Отправляем файлы один за другим
        for file in sorted_files:
            file_path = os.path.join(torrent.save_path, file.name)
            logger.info(f"Отправка файла: {file.name}")

            # Отправляем файл
            with open(file_path, "rb") as f:
                media = InputMediaDocument(f)
                await update.message.reply_media_group(media=[media])
            
            # Удаляем торрент после отправки
            qb.torrents_remove(hashes=[torrent.hash])
            logger.info(f"Торрент {torrent.hash} удален после отправки файлов.")