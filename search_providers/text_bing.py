# search_providers/text_bing.py
from bs4 import BeautifulSoup
import logging
from config import settings
from urllib.parse import quote_plus
from http_clients import get_cffi_session

async def search_bing(query: str, limit: int | None = None) -> list[dict]:
    if limit is None:
        limit = settings.PER_PROVIDER_FETCH_TEXT
    DEFAULT_BING_URL = "https://www.bing.com"
    BASE_URL = settings.BING_REVERSE_PROXY or DEFAULT_BING_URL
    logging.info(f"Using Bing endpoint: {BASE_URL}")
    
    q_enc = quote_plus(query)
    url = f"{BASE_URL}/search?q={q_enc}&mkt=zh-CN"

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Pragma': 'no-cache',
        'Sec-Ch-Ua': '"Not(A:Brand";v="99", "Google Chrome";v="123", "Chromium";v="123"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }
    
    session = get_cffi_session()
    try:
        logging.info(f"Searching Bing with query: '{query}' (limit={limit})")
        response = await session.get(url, headers=headers)
        response.raise_for_status()

        if "验证" in response.text or "verify" in str(response.url).lower():
             logging.error("Bing redirected to a verification page. The request was likely blocked.")
             return []

        soup = BeautifulSoup(response.content, 'html.parser')
        results = []

        for item in soup.select('#b_results > li'):
            if len(results) >= limit:
                break
                
            title_tag = item.select_one('h2 > a')
            if not title_tag:
                continue

            href = title_tag.get('href')
            if not href:
                continue

            title = title_tag.get_text(strip=True)

            desc_container = item.select_one('div.b_caption')
            snippet_text = ""
            if desc_container:
                for unwanted in desc_container.select('cite, .b_attribution'):
                    unwanted.decompose()
                snippet_text = desc_container.get_text(" ", strip=True)

            if title and href:
                results.append({
                    "title": title,
                    "link": href,
                    "snippet": snippet_text
                })
        
        if not results:
            logging.warning(f"Bing search for '{query}' returned 0 results. The page structure might have changed or the request was blocked.")
            
        return results[:limit]
    except Exception as e:
        logging.warning(f"Failed to fetch results from Bing via {BASE_URL}. Reason: {e}")
        return []