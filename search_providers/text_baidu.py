# search_providers/text_baidu.py
import asyncio
import logging
from urllib.parse import quote_plus
import re
from bs4 import BeautifulSoup
from config import settings
from http_clients import get_cffi_session
from curl_cffi.requests import AsyncSession

REAL_URL_PATTERN = re.compile(r'window\.location\.replace\(["\'](.*?)["\']\)')

async def resolve_redirect(session: AsyncSession, redirect_url: str) -> str:
    """解析百度的跳转链接以获取真实URL。复用传入的会话。"""
    if not redirect_url.startswith('http'):
        return redirect_url
    try:
        response = await session.get(redirect_url, timeout=5)
        final_url = str(response.url)
        if 'baidu.com' in final_url:
            match = REAL_URL_PATTERN.search(response.text)
            if match:
                return match.group(1)
        return final_url
    except Exception as e:
        logging.warning(f"Could not resolve Baidu redirect '{redirect_url}': {e}")
        return redirect_url

async def search_baidu(query: str, limit: int | None = None) -> list[dict]:
    if limit is None:
        limit = settings.PER_PROVIDER_FETCH_TEXT
    DEFAULT_BAIDU_URL = "https://www.baidu.com"
    base_url = settings.BAIDU_REVERSE_PROXY or DEFAULT_BAIDU_URL
    logging.info(f"Using Baidu endpoint: {base_url}")
    
    search_url = f"{base_url}/s?wd={quote_plus(query)}"

    session = get_cffi_session()
    try:
        await session.get(base_url)
        
        logging.info(f"Searching Baidu with query: '{query}' (limit={limit})")
        response = await session.get(search_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        
        for item in soup.select('#content_left > div.c-container', limit=limit * 2):
            if len(results) >= limit:
                break
            title_tag = item.select_one('h3 > a')
            if not title_tag: continue
            title = title_tag.get_text(strip=True)
            redirect_link = title_tag.get('href')
            snippet_tag = item.select_one('div > div > div:nth-of-type(2)')
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            if title and redirect_link:
                results.append({"title": title, "link": redirect_link, "snippet": snippet})
        
        redirect_links = [res['link'] for res in results]

        resolve_tasks = [resolve_redirect(session, link) for link in redirect_links]
        real_links = await asyncio.gather(*resolve_tasks, return_exceptions=True)

        final_results = []
        for i, res in enumerate(results):
            if not isinstance(real_links[i], Exception):
                res['link'] = real_links[i]
                final_results.append(res)
        
        return final_results[:limit]

    except Exception as e:
        logging.error(f"Error searching Baidu via {base_url}: {e}", exc_info=True)
        return []