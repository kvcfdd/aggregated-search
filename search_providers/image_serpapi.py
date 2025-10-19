# search_providers/image_serpapi.py
import logging
import threading
from config import settings
from http_clients import get_httpx_client
import httpx

# SerpApi
SERPAPI_BASE_URL = "https://serpapi.com/search"

serpapi_keys = []
if settings.SERPAPI_API_KEYS and "default" not in settings.SERPAPI_API_KEYS:
    serpapi_keys = [key.strip() for key in settings.SERPAPI_API_KEYS.split(',')]

key_index = 0
key_lock = threading.Lock()

def get_next_serpapi_key() -> str | None:
    global key_index
    if not serpapi_keys:
        return None
    with key_lock:
        key_to_use = serpapi_keys[key_index]
        key_index = (key_index + 1) % len(serpapi_keys)
        return key_to_use

async def search_images_serpapi(query: str, limit: int | None = None) -> list[dict]:
    if limit is None:
        limit = settings.PER_PROVIDER_FETCH_IMAGE
    api_key = get_next_serpapi_key()
    if not api_key:
        logging.error("SerpApi API keys not configured or list is empty. Image search is disabled.")
        return []

    # 获取全局共享的 httpx 客户端
    client = get_httpx_client()
    
    # 构建请求参数
    params = {
        "q": query,
        "engine": "google_images",
        "api_key": api_key,
        "num": limit,
        "output": "json"
    }
    
    try:
        logging.info(f"Searching images with SerpApi key ending in '...{api_key[-4:]}'.")

        response = await client.get(SERPAPI_BASE_URL, params=params)
        response.raise_for_status()
        
        results = response.json()
        
        image_results = []
        if 'images_results' in results:
            for item in results.get('images_results', []):
                image_results.append({
                    "title": item.get("title"),
                    "source": item.get("source"),
                    "link": item.get("link"),
                    "original": item.get("original"),
                    "thumbnail": item.get("thumbnail"),
                })
        return image_results
        
    # 捕获 httpx 可能抛出的特定异常
    except httpx.HTTPStatusError as e:
        logging.error(f"HTTP error from SerpApi: {e.response.status_code} - {e.response.text}", exc_info=True)
        return []
    except Exception as e:
        logging.error(f"Error searching images with SerpApi via httpx: {e}", exc_info=True)
        return []