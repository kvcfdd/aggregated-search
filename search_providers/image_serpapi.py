# search_providers/image_serpapi.py
from serpapi import GoogleSearch
from config import settings
import logging
import threading

serpapi_keys = []
if settings.SERPAPI_API_KEYS and "default" not in settings.SERPAPI_API_KEYS:
    serpapi_keys = [key.strip() for key in settings.SERPAPI_API_KEYS.split(',')]
key_index = 0
key_lock = threading.Lock()
def get_next_serpapi_key() -> str | None:
    global key_index
    if not serpapi_keys: return None
    with key_lock:
        key_to_use = serpapi_keys[key_index]
        key_index = (key_index + 1) % len(serpapi_keys)
        return key_to_use

def search_images_serpapi(query: str, limit: int) -> list[dict]:
    api_key = get_next_serpapi_key()
    if not api_key:
        logging.error("SerpApi API keys not configured or list is empty.")
        return []

    params = {
        "q": query,
        "engine": "google_images",
        "api_key": api_key,
        "num": limit
    }
    
    try:
        logging.info(f"Using SerpApi key ending with '...{api_key[-4:]}' via default URL.")
        search = GoogleSearch(params)
        results = search.get_dict()
        
        image_results = []
        if 'images_results' in results:
            for item in results['images_results']:
                image_results.append({
                    "title": item.get("title"),
                    "source": item.get("source"),
                    "link": item.get("link"),
                    "original": item.get("original"),
                    "thumbnail": item.get("thumbnail"),
                })
        return image_results
    except Exception as e:
        logging.error(f"Error searching images with SerpApi: {e}")
        return []