# search_providers/image_bing.py
import json
import logging
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from config import settings
from http_clients import get_cffi_session


async def parse_bing_image_results(soup: BeautifulSoup) -> list[dict]:
    results = []
    for item in soup.select("div.iuscp"):
        link_tag = item.select_one("a.iusc")
        if not link_tag:
            continue
        m_attr = link_tag.get("m")
        if not m_attr:
            continue
        try:
            data = json.loads(m_attr)
            original_url, page_url, title, thumbnail_url = data.get("murl"), data.get("purl"), data.get("t"), data.get("turl")
            if original_url and title:
                results.append({
                    "title": title, "source": page_url, "link": page_url,
                    "original": original_url, "thumbnail": thumbnail_url,
                })
        except (json.JSONDecodeError, AttributeError) as e:
            logging.warning(f"Failed to parse image data from Bing: {e}")
            continue
    return results


async def search_bing_images(query: str, limit: int | None = None) -> list[dict]:
    if limit is None:
        limit = settings.PER_PROVIDER_FETCH_IMAGE
    """异步地从 Bing.com 直接抓取图片搜索结果。"""
    DEFAULT_BING_URL = "https://www.bing.com"
    BASE_URL = settings.BING_REVERSE_PROXY or DEFAULT_BING_URL
    
    search_url = f"{BASE_URL}/images/search?q={quote_plus(query)}&mkt=zh-CN&first=1"
    logging.info(f"Searching Bing Images with query: '{query}'")

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': BASE_URL + "/",
        'sec-ch-ua': '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
    }
    
    session = get_cffi_session()
    all_results = []
    
    try:
        logging.info("Warming up Bing session to get initial cookies for image search...")
        await session.get(BASE_URL, headers=headers, impersonate="edge101")

        response = await session.get(search_url, headers=headers, impersonate="edge101")
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        all_results.extend(await parse_bing_image_results(soup))
        
        next_url_container = soup.select_one("#mmComponent_images_1[data-nextUrl]")
        next_url = next_url_container.get("data-nextUrl") if next_url_container else None

        while next_url and len(all_results) < limit:
            async_url = urljoin(BASE_URL, next_url)
            logging.info(f"Fetching next page from Bing Images: {async_url}")
            
            # 请求带上完整的头信息
            async_response = await session.get(async_url, headers=headers, impersonate="edge101")
            async_response.raise_for_status()
            
            async_soup = BeautifulSoup(async_response.content, 'html.parser')
            
            page_results = await parse_bing_image_results(async_soup)
            if not page_results:
                break
                
            all_results.extend(page_results)
            
            next_container = async_soup.select_one(".dgControl[data-nextUrl]")
            next_url = next_container.get("data-nextUrl") if next_container else None

        if not all_results:
            logging.warning(f"Bing Images search for '{query}' returned 0 results.")
        
        return all_results[:limit]

    except Exception as e:
        logging.warning(f"Failed to fetch results from Bing via {BASE_URL}. Reason: {e}")
        return []