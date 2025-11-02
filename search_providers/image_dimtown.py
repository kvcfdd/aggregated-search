# search_providers/image_dimtown.py
import asyncio
import logging
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from config import settings
from http_clients import get_cffi_session

DEFAULT_DIMTOWN_URL = "https://dimtown.com"
BASE_URL = settings.DIMTOWN_REVERSE_PROXY or DEFAULT_DIMTOWN_URL

async def get_images_from_detail_page(session: AsyncSession, detail_url: str) -> list[dict]:
    try:
        response = await session.get(detail_url, impersonate="chrome120", timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 提取文章标题作为图片的基础标题
        post_title_tag = soup.select_one("h1")
        base_title = post_title_tag.get_text(strip=True) if post_title_tag else "无标题"

        # 定位到包含图片的核心内容区域
        content_div = soup.select_one("div.content#content")
        if not content_div:
           # logging.warning(f"在页面 {detail_url} 中未找到ID为 'content' 的内容区域")
            return []

        images = []
        # 图片链接位于 a 标签中
        image_links = content_div.select("p > a[href]")

        for i, link in enumerate(image_links):
            # 确保 a 标签下真的有图片
            if not link.find("img"):
                continue

            image_url = link.get("href")
            # 简单判断链接是否为图片
            if image_url and any(ext in image_url for ext in ['.webp', '.jpg', '.jpeg', '.png', '.gif']):
                img_tag = link.find("img")
                alt_text = img_tag.get("alt", "").strip() if img_tag else ""
                
                final_title = alt_text if alt_text else f"{base_title} - 图{i+1}"

                images.append({
                    "title": final_title,
                    "source": detail_url,
                    "link": detail_url,
                    "original": image_url,
                    "thumbnail": image_url,
                })

        return images
    except Exception as e:
        logging.error(f"处理次元小镇详情页 {detail_url} 时发生错误: {e}")
        return []

async def search_dimtown_images(query: str, limit: int | None = None) -> list[dict]:
    if limit is None:
        limit = settings.PER_PROVIDER_FETCH_IMAGE
    # 此处的 limit 用于控制检查的文章数量，以避免过多的请求
    post_limit = 10 
    
    search_url = f"{BASE_URL}/?s={quote_plus(query)}"
    # logging.info(f"正在使用查询词搜索次元小镇: '{query}'")
    session = get_cffi_session()

    try:
        # 获取搜索结果页，得到文章列表
        response = await session.get(search_url, impersonate="chrome120", timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 定位到包含文章列表的区域
        post_items = soup.select("div.update_area ul.update_area_lists > li")
        if not post_items:
           # logging.warning(f"次元小镇未能找到关于 '{query}' 的任何文章。")
            return []

        tasks = []
        for item in post_items[:post_limit]:
            link_tag = item.select_one("a[href]")
            if not link_tag:
                continue
            
            detail_url = link_tag.get("href")
            if detail_url:
                # 创建并发任务，抓取每个详情页
                tasks.append(get_images_from_detail_page(session, detail_url))

        if not tasks:
           # logging.warning(f"从次元小镇搜索结果中未能提取到任何有效的文章链接。")
            return []
            
        # 并发执行所有详情页的抓取任务
       # logging.info(f"发现 {len(tasks)} 篇文章，正在并发抓取图片...")
        results_from_pages = await asyncio.gather(*tasks)

        # 将所有页面返回的图片列表合并成一个扁平的列表
        all_images = [image for page_images in results_from_pages for image in page_images]
        
       # logging.info(f"成功从次元小镇抓取到 {len(all_images)} 张图片。")
        return all_images

    except Exception as e:
        logging.warning(f"从次元小镇抓取结果时失败. 原因: {e}")
        return []