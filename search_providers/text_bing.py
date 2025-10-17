# search_providers/text_bing.py
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup
import logging
from config import settings

async def search_bing(query: str, limit: int) -> list[dict]:
    DEFAULT_BING_URL = "https://www.bing.com"
    BASE_URL = settings.BING_REVERSE_PROXY or DEFAULT_BING_URL
    logging.info(f"Using Bing endpoint: {BASE_URL}")
    url = f"{BASE_URL}/search?q={query}&mkt=zh-CN"

    # 使用 AsyncSession 并模拟 chrome120，这会自动处理所有指纹和Cookie
    async with AsyncSession(impersonate="chrome120", timeout=20) as session:
        try:
            logging.info(f"Searching Bing with query: '{query}'")
            response = await session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            for item in soup.select('#b_results > li.b_algo', limit=limit):
                title_tag = item.select_one('h2 > a')
                snippet_container = item.select_one('div.b_caption')
                snippet_text = ""

                if snippet_container:
                    # 移除摘要中的干扰项
                    for unwanted in snippet_container.select('.b_vlist2col, .b_tpcn'):
                        unwanted.decompose()
                    snippet_text = snippet_container.get_text(" ", strip=True)

                if title_tag:
                    results.append({
                        "title": title_tag.get_text(strip=True),
                        "link": title_tag.get('href'),
                        "snippet": snippet_text
                    })
            
            if not results:
                logging.warning(f"Bing search for '{query}' returned 0 results.")
                
            return results
        except Exception as e:
            logging.error(f"Error searching Bing via {BASE_URL}: {e}", exc_info=True)
            return []