# page_parser.py
import logging
import re
from bs4 import BeautifulSoup, Tag
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
        
        all_content_parts = [summary_text]

        first_heading = soup.select_one("div.paraTitle_A4zIw.level-1_vALZK")

        if first_heading:
            heading_text = first_heading.get_text(strip=True)
            if heading_text:
                all_content_parts.append(heading_text)

            for sibling in first_heading.find_next_siblings():
                if not isinstance(sibling, Tag):
                    continue

                if 'level-1_vALZK' in sibling.get('class', []):
                    break

                for sup in sibling.select('sup'):
                    sup.decompose()

                sibling_text = sibling.get_text(separator='\n', strip=True)
                if sibling_text:
                    all_content_parts.append(sibling_text)

        full_content = "\n\n".join(filter(None, all_content_parts))
        
        return full_content if full_content else None

    except Exception as e:
        logging.warning(f"解析百科页面 {url} 时发生严重错误: {e}")
        return None

async def fetch_and_clean_page_content(url: str) -> str | None:
    session = get_cffi_session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    }
    try:
        logging.info(f"正在进行深度请求，抓取通用页面: {url}")
        response = await session.get(url, headers=headers, impersonate="edge101", timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        # 提取页面标题
        page_title = soup.title.get_text(strip=True) if soup.title else ""
        # 移除常见的噪音元素
        selectors_to_remove = [
            "script", "style", "header", "footer", "nav", "aside", "form", "button",
            ".navbar", ".menu", ".sidebar", ".ad", ".ads", ".advertisement",
            "#comments", ".comments", ".comment-section",
            ".related-posts", ".related", ".footer-links", ".social-links",
            "iframe", "noscript"
        ]
        for selector in selectors_to_remove:
            for element in soup.select(selector):
                element.decompose()

        # 尝试定位主要内容区域
        main_content_area = (
            soup.find("main") or
            soup.find("article") or
            soup.select_one("[role='main']") or
            soup.select_one("#content, .content, #main, .main-content, .post, .entry-content, .article-body, #article")
        )
        # 如果找不到特定区域，则回退到 body
        extraction_target = main_content_area if main_content_area else soup.body
        if not extraction_target:
            # 如果连 body 都没有，返回标题
            return page_title.strip() if page_title else None
        # 从目标区域提取文本
        body_text = extraction_target.get_text(separator='\n', strip=True)
        # 处理文本，移除多余的空行
        cleaned_text = re.sub(r'(\n\s*){3,}', '\n\n', body_text)
        # 组合标题和正文
        full_content = f"{page_title}\n\n{cleaned_text}"
        return full_content.strip()

    except Exception as e:
        logging.warning(f"解析通用页面 {url} 时发生严重错误: {e}")
        return None