# search_providers/text_ddg.py
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import logging
from config import settings

DEFAULT_DDG_URL = "https://html.duckduckgo.com"
BASE_URL = settings.DDG_REVERSE_PROXY or DEFAULT_DDG_URL
logging.info(f"Using DuckDuckGo endpoint: {BASE_URL}")

async def search_ddg(query: str, limit: int = 15) -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    }
    q_enc = quote_plus(query)
    url = f"{BASE_URL}/html/?q={q_enc}"
    
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
            logging.info(f"Searching DDG with query: '{query}' (limit={limit})")
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # DDG HTML 版本的结果项选择器
        for item in soup.find_all('div', class_='result', limit=limit):
            title_tag = item.find('a', class_='result__a')
            snippet_tag = item.find('a', class_='result__snippet')
            
            if title_tag and snippet_tag:
                href = title_tag.get('href')
                # 如果链接是相对路径，则拼接成绝对路径
                if href and href.startswith('/'):
                    href = BASE_URL.rstrip('/') + href
                results.append({
                    "title": title_tag.text.strip(),
                    "link": href,
                    "snippet": snippet_tag.text.strip()
                })
        return results
    except Exception as e:
        logging.error(f"Error searching DuckDuckGo via {BASE_URL}: {e}", exc_info=True)
        return []