# search_providers/text_ddg.py
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import logging
from config import settings
from http_clients import get_httpx_client

DEFAULT_DDG_URL = "https://html.duckduckgo.com"
BASE_URL = settings.DDG_REVERSE_PROXY or DEFAULT_DDG_URL
logging.info(f"Using DuckDuckGo endpoint: {BASE_URL}")

async def search_ddg(query: str, limit: int | None = None) -> list[dict]:
    if limit is None:
        limit = settings.PER_PROVIDER_FETCH_TEXT
    q_enc = quote_plus(query)
    url = f"{BASE_URL}/html/?q={q_enc}"
    
    try:
        client = get_httpx_client()
        logging.info(f"Searching DDG with query: '{query}' (limit={limit})")
        response = await client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        for item in soup.find_all('div', class_='result', limit=limit):
            title_tag = item.find('a', class_='result__a')
            snippet_tag = item.find('a', class_='result__snippet')
        
            if title_tag and snippet_tag:
                href = title_tag.get('href')
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