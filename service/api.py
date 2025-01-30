import requests
import urllib.parse
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", 'w', 'utf-8'),  # Логирование в файл
        logging.StreamHandler()  # Логирование в консоль
    ]
)
logger = logging.getLogger(__name__)

API = "https://anilibria.top/api/v1"

class Anime:
    @staticmethod
    async def search(name):
        # Кодируем строку name для корректного включения в URL
        encoded_name = urllib.parse.quote(name)
        logger.info(f"Выполняется поиск аниме по запросу: {name}")

        try:
            response = requests.get(f"{API}/app/search/releases?query={encoded_name}")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Успешно получены данные для запроса: {name}")

            # Извлекаем данные из ответа сервера
            anime_list = [
                {
                    "id": anime["id"],
                    "name": anime["name"]["main"]
                } for anime in data
            ]
            logger.info(f"Найденные тайлы: {anime_list}")
            logger.info(f"Найдено {len(anime_list)} результатов для запроса: {name}")
            return anime_list
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при выполнении запроса поиска для '{name}': {e}")
            return []
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при обработке запроса поиска для '{name}': {e}")
            return []

    @staticmethod
    async def get_title(title_id):
        logger.info(f"Запрос информации об аниме с ID: {title_id}")

        try:
            response = requests.get(f"{API}/anime/releases/{title_id}")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Успешно получены данные для аниме с ID: {title_id}")

            episodes = [
                {
                    "title_id": data['id'],
                    "title_name": data['name']['main'],
                    "description": data['description'],
                    "poster": data['poster']['src'],
                    # "genres": data['genres']
                }
            ]
            logger.info(f"Успешно обработаны данные для аниме с ID: {title_id}")
            return episodes
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при выполнении запроса информации для аниме с ID {title_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при обработке запроса информации для аниме с ID {title_id}: {e}")
            return []
        
    @staticmethod
    async def get_torrent(title_id):
        logger.info(f"Запрос информации о торренте для аниме с ID: {title_id}")

        try:
            response = requests.get(f"{API}/anime/releases/{title_id}")
            response.raise_for_status()
            data = response.json()

            if "torrents" not in data:
                logger.error(f"Ошибка: ключ 'torrents' не найден в ответе API")
                return []

            torrents = data["torrents"]
            if not isinstance(torrents, list):
                logger.error(f"Ошибка: 'torrents' должен быть списком, но получен {type(torrents)}")
                return []

            torrent_list = []
            for torrent in torrents:
                quality = f"{torrent['type']['description']} {torrent['quality']['value']}"
                if 'HEVC' in torrent['codec']['value']:
                    quality += " hevc"
                size_gb = torrent['size'] / (1024 ** 3)

                torrent_list.append({
                    "quality": quality,
                    "size": f"{size_gb:.2f} GB",
                    "torrent_id": torrent["id"]
                })

            return torrent_list

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            return []
        except Exception as e:
            logger.error(f"Непредвиденная ошибка: {e}")
            return []

    @staticmethod  
    async def download_torrent(torrent_id, title_id):
        logger.info(f"Запрос информации о торренте с ID: {torrent_id} для аниме с ID: {title_id}")

        try:
            response = requests.get(f"{API}/anime/releases/{title_id}")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Успешно получены данные о торренте для аниме с ID: {title_id}")

            if "torrents" not in data:
                logger.error("Ошибка: ключ 'torrents' не найден в ответе API")
                return None

            torrents = data["torrents"]
            if not isinstance(torrents, list):
                logger.error(f"Ошибка: 'torrents' должен быть списком, но получен {type(torrents)}")
                return None

            # Отладка: вывод всех ID торрент-файлов
            available_ids = [torrent["id"] for torrent in torrents]
            logger.debug(f"Список доступных ID торрентов: {available_ids}")
            
            # Преобразуем torrent_id в int, если он вдруг строка
            torrent_id = int(torrent_id)

            for torrent in torrents:
                logger.debug(f"Проверка торрент-файла: {torrent['id']} == {torrent_id}")
                if torrent["id"] == torrent_id:
                    magnet = torrent["magnet"]
                    magnet_hash = torrent["hash"]
                    logger.info(f"Найден торрент {torrent_id}, магнет-ссылка: {magnet}")
                    return magnet, magnet_hash

            logger.error(f"Торрент с ID {torrent_id} не найден для аниме с ID {title_id}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            return None
        except ValueError as e:
            logger.error(f"Ошибка преобразования ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка: {e}")
            return None