# search_providers/image_acg66.py
import logging
import asyncio
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

from config import settings
from http_clients import get_cffi_session

# 网站的基础URL
DEFAULT_ACG66_URL = "https://www.acg66.com"
BASE_URL = settings.ACG66_REVERSE_PROXY or DEFAULT_ACG66_URL

async def get_images_from_post(session: AsyncSession, post_url: str) -> list[dict]:
    try:
        logging.info(f"Fetching image details from post page: {post_url}")
        response = await session.get(post_url, impersonate="chrome120", timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        title_tag = soup.select_one("h1.tit")
        title = title_tag.get_text(strip=True) if title_tag else "Untitled"
        
        results = []

        image_spans = soup.select("span.LightGallery_Item[lg-data-src]")
        
        if image_spans:
            logging.info(f"Primary method success: Found {len(image_spans)} 'LightGallery_Item' spans on {post_url}")
            for i, span in enumerate(image_spans):
                original_url = span.get("lg-data-src")
                if original_url:
                    full_original_url = urljoin(BASE_URL, original_url)
                    results.append({
                        "title": f"{title} (p{i+1})" if len(image_spans) > 1 else title,
                        "source": post_url, "link": post_url,
                        "original": full_original_url, "thumbnail": full_original_url,
                    })
            return results

        logging.warning(f"No 'LightGallery_Item' spans found on {post_url}. Trying fallback method.")
        content_body = soup.select_one("div.umBody")
        if not content_body:
            logging.error(f"Fallback failed: Could not find content body 'div.umBody' on {post_url}")
            return []

        image_tags = content_body.select("img[src]")
        if not image_tags:
            logging.warning(f"Fallback method also failed: No valid img tags found in 'div.umBody' on {post_url}")
            return []

        logging.info(f"Fallback method success: Found {len(image_tags)} 'img' tags on {post_url}")
        for i, img in enumerate(image_tags):
            original_url = img.get('src')
            if original_url and original_url.startswith('http') and '/zb_users/' in original_url:
                full_original_url = urljoin(BASE_URL, original_url)
                results.append({
                    "title": f"{title} (p{i+1})" if len(image_tags) > 1 else title,
                    "source": post_url, "link": post_url,
                    "original": full_original_url, "thumbnail": full_original_url,
                })
        
        return results
        
    except Exception as e:
        logging.error(f"Failed to process post page {post_url}. Reason: {e}")
        return []


async def search_acg66_images(query: str, limit: int | None = None) -> list[dict]:
    if limit is None:
        limit = settings.PER_PROVIDER_FETCH_IMAGE
        
    session = get_cffi_session()
    search_url = f"{BASE_URL}/search.php?q={quote_plus(query)}"
    
    all_results = []
    
    try:
        # 请求搜索结果页，获取文章链接
        logging.info(f"Searching acg66.com with query: '{query}'")
        response = await session.get(search_url, impersonate="chrome120")
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找目标
        post_links = soup.select("article.post .umPic > a")
        
        if not post_links:
            logging.warning(f"ACG66 search for '{query}' returned 0 post links.")
            return []

        post_urls = [urljoin(BASE_URL, link.get('href')) for link in post_links if link.get('href')]
        logging.info(f"Found {len(post_urls)} potential post pages from search results.")

        # 并发请求所有文章页面
        tasks = [get_images_from_post(session, url) for url in post_urls]
        
        # 并发执行所有抓取任务
        results_from_pages = await asyncio.gather(*tasks)
        
        # 将嵌套的列表展平为单个列表
        for page_result in results_from_pages:
            all_results.extend(page_result)
            if len(all_results) >= limit:
                break
        logging.info(f"Successfully fetched {len(all_results)} total images from acg66 for query '{query}'.")
        # 返回裁剪到上限数量的结果
        return all_results[:limit]

    except Exception as e:
        logging.error(f"An error occurred during acg66 image search for '{query}'. Reason: {e}")
        return []