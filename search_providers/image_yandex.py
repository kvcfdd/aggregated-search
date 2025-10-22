# search_providers/image_yandex.py
import json
import logging
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from config import settings
from http_clients import get_cffi_session


async def search_yandex_images(query: str, limit: int | None = None) -> list[dict]:
    if limit is None:
        limit = settings.PER_PROVIDER_FETCH_IMAGE

    DEFAULT_YANDEX_URL = "https://yandex.com"
    BASE_URL = settings.YANDEX_REVERSE_PROXY or DEFAULT_YANDEX_URL
    search_url = f"{BASE_URL}/images/search?text={quote_plus(query)}"

    logging.info(f"Searching Yandex Images with query: '{query}'")

    session = get_cffi_session()

    try:
        response = await session.get(search_url, impersonate="chrome120", timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        data_div = soup.select_one('div[id^="ImagesApp-"]')
        if not data_div:
            logging.warning("Yandex Images: Could not find the main data div. Page structure might have changed.")
            return []

        data_state = data_div.get('data-state')
        if not data_state:
            logging.warning("Yandex Images: data-state attribute is missing from the main data div.")
            return []

        data = json.loads(data_state)
        
        results = []
        items_entities = data.get('initialState', {}).get('serpList', {}).get('items', {}).get('entities', {})
        
        if not items_entities:
            logging.warning("Yandex Images: Could not find 'entities' in the parsed JSON data.")
            return []

        for item_id, item_data in items_entities.items():
            if len(results) >= limit:
                break
            
            snippet = item_data.get('snippet', {})
            title = snippet.get('title')
            original_url = item_data.get('origUrl')
            source_url = snippet.get('url')
            thumbnail_url = item_data.get('image')

            if not all([title, original_url, source_url]):
                continue

            if thumbnail_url and thumbnail_url.startswith('//'):
                thumbnail_url = 'https:' + thumbnail_url

            results.append({
                "title": title,
                "source": source_url,
                "link": source_url,
                "original": original_url,
                "thumbnail": thumbnail_url,
            })
            
        logging.info(f"Successfully fetched {len(results)} images from Yandex.")
        return results

    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from Yandex Images page: {e}")
        return []
    except (KeyError, TypeError) as e:
        logging.error(f"Yandex Images: Unexpected JSON structure. Failed to navigate to items. Error: {e}")
        return []
    except Exception as e:
        logging.warning(f"Failed to fetch results from Yandex via {BASE_URL}. Reason: {e}")
        return []