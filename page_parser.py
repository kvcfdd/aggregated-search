# page_parser.py
import logging
from bs4 import BeautifulSoup
from http_clients import get_cffi_session

async def fetch_baike_content(url: str) -> str | None:
    if "baike.baidu.com" not in url:
        return None
    
    session = get_cffi_session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    try:
        logging.info(f"正在增强内容，抓取百科页面: {url}")
        response = await session.get(url, headers=headers, impersonate="edge101", timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        summary_div = soup.select_one('div.lemmaSummary_vu0OO')

        if not summary_div:
            return None

        for sup in summary_div.select('sup'):
            sup.decompose()

        summary_text = summary_div.get_text(separator='\n', strip=True)
        
        if summary_text:
            return summary_text
        else:
            return None

    except Exception as e:
        logging.error(f"抓取或解析百科页面 {url} 时发生严重错误: {e}", exc_info=True)
        return None