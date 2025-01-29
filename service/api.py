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

API = "https://api.anilibria.tv/v3"

class Anime:
    @staticmethod
    async def search(name):
        # Кодируем строку name для корректного включения в URL
        encoded_name = urllib.parse.quote(name)
        logger.info(f"Выполняется поиск аниме по запросу: {name}")

        try:
            response = requests.get(f"{API}/title/search?search={encoded_name}&filter=id,names,team,genres[0]&limit=10")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Успешно получены данные для запроса: {name}")

            # Извлекаем данные из ответа сервера
            anime_list = [
                {
                    "id": anime["id"],
                    "name": anime["names"]["ru"]
                } for anime in data["list"]
            ]
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
            response = requests.get(f"{API}/title?id={title_id}")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Успешно получены данные для аниме с ID: {title_id}")

            episodes = [
                {
                    "title_id": title_id,
                    "title_name": data['names']['ru'],
                    "description": data['description'],
                    "poster": data['posters']['original']['url'],
                    "genres": data['genres']
                }
            ]
            for play in data['player']['list'].values():
                # Приоритетное получение ссылки
                link = (
                    play['hls'].get('fhd') or
                    play['hls'].get('hd') or
                    play['hls'].get('sd')
                )
                episodes.append({
                    "episode": play['episode'],
                    "name": play['name'] if play['name'] is not None else "Нет названия",
                    "link": link,
                })
            logger.info(f"Успешно обработаны данные для аниме с ID: {title_id}")
            return episodes
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при выполнении запроса информации для аниме с ID {title_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при обработке запроса информации для аниме с ID {title_id}: {e}")
            return []
        
    async def get_torrent(title_id):
        logger.info(f"Запрос информации о торренте для аниме с ID: {title_id}")

        try:
            response = requests.get(f"{API}/title?id={title_id}&filter=torrents")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Успешно получены данные о торренте для аниме с ID: {title_id}")

            torrents = [
                {
                    "quality": torrent['quality']['string'],
                    "size": torrent['size_string'],
                    "magnet": torrent['magnet']
                } for torrent in data['torrents']['list']
            ]

            print(torrents)

            return torrents
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при выполнении запроса информации о торренте для аниме с ID {title_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при обработке запроса информации о торренте для аниме с ID {title_id}: {e}")
            return []