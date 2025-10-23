# page_parser.py
import logging
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

        # 移除脚本、样式、导航、页眉页脚等噪音元素
        for element in soup(["script", "style", "header", "footer", "nav", "aside"]):
            element.decompose()

        # 获取body中的文本，移除所有HTML标签
        body = soup.body
        if body:
            # 使用空格作为分隔符，避免单词错误地连接在一起
            text = body.get_text(separator=' ', strip=True)
            return text
        
        return None

    except Exception as e:
        logging.warning(f"解析通用页面 {url} 时发生严重错误: {e}")
        return None