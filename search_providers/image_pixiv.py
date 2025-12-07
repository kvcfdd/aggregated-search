# search_providers/image_pixiv.py
import asyncio
import logging
from urllib.parse import quote_plus
from config import settings
from http_clients import get_cffi_session
from curl_cffi.requests import AsyncSession

def rewrite_image_url(url: str | None) -> str | None:
    if not url:
        return None
    
    img_proxy = settings.PIXIV_IMG_REVERSE_PROXY
    if img_proxy:
        img_proxy = img_proxy.rstrip('/')
        return url.replace("https://i.pximg.net", img_proxy)
    return url

async def get_artwork_details(
    session: AsyncSession, 
    artwork_id: str, 
    api_endpoint: str, 
    public_base_url: str
) -> list[dict] | None:
    detail_url = f"{api_endpoint}/ajax/illust/{artwork_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Referer': f'{api_endpoint}/artworks/{artwork_id}',
        'Accept': 'application/json',
    }
    try:
        response = await session.get(detail_url, headers=headers, timeout=4)
        if response.status_code == 404:
            logging.warning(f"Pixiv artwork {artwork_id} not found (404).")
            return None
        response.raise_for_status()
        data = response.json()
        
        if data.get("error"):
            logging.warning(f"Pixiv API error for {artwork_id}: {data.get('message')}")
            return None
            
        artwork_body = data.get("body", {})
        # page_count = artwork_body.get("pageCount", 1)

        original_url_template = artwork_body.get("urls", {}).get("original")
        thumbnail_url = artwork_body.get("urls", {}).get("regular")

        if not original_url_template:
            return None

        results = []
        page_url = f'{public_base_url}/artworks/{artwork_id}'
        
        # 仅获取第一张图片
        final_original_url = rewrite_image_url(original_url_template)
        final_thumbnail_url = rewrite_image_url(thumbnail_url)

        results.append({
            "title": artwork_body.get("title"),
            "source": page_url,
            "link": page_url,
            "original": final_original_url,
            "thumbnail": final_thumbnail_url,
        })
            
        return results
    except Exception as e:
        logging.error(f"Failed to get details for Pixiv artwork {artwork_id}: {e}")
        return None

async def search_pixiv_images(query: str, limit: int | None = None) -> list[dict]:
    if limit is None:
        limit = settings.PER_PROVIDER_FETCH_IMAGE
    
    PUBLIC_BASE_URL = "https://www.pixiv.net"
    API_ENDPOINT = settings.PIXIV_REVERSE_PROXY or PUBLIC_BASE_URL
    
    encoded_query = quote_plus(query)
    
    logging.info(f"Step 1: Searching Pixiv for artworks with tag: '{query}' using endpoint: {API_ENDPOINT}")

    search_headers = {
        'accept': 'application/json',
        'referer': f'{API_ENDPOINT}/tags/{encoded_query}/artworks',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }

    session = get_cffi_session()
    artwork_ids = []
    current_page = 1
    
    try:
        while len(artwork_ids) < limit and current_page <= 5:
            search_url = f"{API_ENDPOINT}/ajax/search/artworks/{encoded_query}?word={encoded_query}&order=date_d&mode=all&p={current_page}&s_mode=s_tag"
            
            logging.info(f"Fetching Pixiv artwork IDs from page {current_page}...")
            response = await session.get(search_url, headers=search_headers, timeout=6)
            response.raise_for_status()
            data = response.json()

            artworks = data.get("body", {}).get("illustManga", {}).get("data", [])
            if not artworks:
                break
                
            for art in artworks:
                if art.get("id"):
                    artwork_ids.append(art["id"])

            current_page += 1
            await asyncio.sleep(0.2)

        if not artwork_ids:
            logging.warning(f"Could not find any Pixiv artwork IDs for tag '{query}'.")
            return []

        logging.info(f"Step 2: Concurrently fetching details for {len(artwork_ids)} artworks...")
        
        tasks = [
            get_artwork_details(session, art_id, API_ENDPOINT, PUBLIC_BASE_URL) 
            for art_id in artwork_ids
        ]
        results_nested = await asyncio.gather(*tasks)

        final_results = [item for sublist in results_nested if sublist for item in sublist]
        
        logging.info(f"Successfully fetched {len(final_results)} original images from Pixiv.")
        return final_results

    except Exception as e:
        logging.warning(f"Failed to fetch results from Pixiv via {PUBLIC_BASE_URL}. Reason: {e}")
        return []
