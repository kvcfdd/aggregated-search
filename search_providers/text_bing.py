# search_providers/text_bing.py
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup
import logging
from config import settings
from urllib.parse import quote_plus

async def search_bing(query: str, limit: int = 15) -> list[dict]:
    DEFAULT_BING_URL = "https://www.bing.com"
    BASE_URL = settings.BING_REVERSE_PROXY or DEFAULT_BING_URL
    logging.info(f"Using Bing endpoint: {BASE_URL}")
    
    q_enc = quote_plus(query)
    url = f"{BASE_URL}/search?q={q_enc}&mkt=zh-CN"
    # 使用 impersonate 参数模拟 Chrome 浏览器
    async with AsyncSession(impersonate="chrome120", timeout=20) as session:
        try:
            logging.info(f"Searching Bing with query: '{query}' (limit={limit})")
            response = await session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Bing 的搜索结果项选择器
            for item in soup.select('#b_results > li.b_algo', limit=limit):
                title_tag = item.select_one('h2 > a')
                snippet_container = item.select_one('div.b_caption')
                snippet_text = ""

                if snippet_container:
                    # 移除摘要中无关的元素（如“相关视频”列表），以获得更纯净的文本
                    for unwanted in snippet_container.select('.b_vlist2col, .b_tpcn'):
                        unwanted.decompose()
                    snippet_text = snippet_container.get_text(" ", strip=True)

                if title_tag:
                    href = title_tag.get('href')
                    # 如果链接是相对路径，则拼接成绝对路径
                    if href and href.startswith('/'):
                        href = BASE_URL.rstrip('/') + href
                    results.append({
                        "title": title_tag.get_text(strip=True),
                        "link": href,
                        "snippet": snippet_text
                    })
            
            if not results:
                logging.warning(f"Bing search for '{query}' returned 0 results. The page structure might have changed.")
                
            return results
        except Exception as e:
            logging.error(f"Error searching Bing via {BASE_URL}: {e}", exc_info=True)
            return []