# search_providers/text_bing.py
import httpx
from bs4 import BeautifulSoup
import logging
from config import settings

DEFAULT_BING_URL = "https://www.bing.com"
BASE_URL = settings.BING_REVERSE_PROXY or DEFAULT_BING_URL
logging.info(f"Using Bing endpoint: {BASE_URL}")

async def search_bing(query: str, limit: int) -> list[dict]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    }
    url = f"{BASE_URL}/search?q={query}"
    
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for item in soup.select('li.b_algo', limit=limit):
            title_tag = item.select_one('h2 a')
            snippet_tag = item.select_one('.b_caption p')
            
            if title_tag and snippet_tag:
                results.append({
                    "title": title_tag.get_text(),
                    "link": title_tag.get('href'),
                    "snippet": snippet_tag.get_text()
                })
        return results
    except Exception as e:
        logging.error(f"Error searching Bing via {BASE_URL}: {e}")
        return []