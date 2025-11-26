# page_parser.py
import logging
import re
from bs4 import BeautifulSoup
from readability import Document
from markdownify import markdownify as md
from http_clients import get_cffi_session

async def fetch_and_clean_page_content(url: str, referer: str | None = None) -> str | None:
    """
    深度抓取网页，使用 readability 提取核心内容，
    并转换为 Markdown 格式，保留文章结构供 LLM 阅读。
    """
    session = get_cffi_session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    if referer:
        headers['Referer'] = referer

    try:
        logging.info(f"正在深度抓取页面: {url}")
        # 下载静态 HTML
        response = await session.get(url, headers=headers, impersonate="edge101", timeout=15)
        
        # 处理非 200 响应
        if response.status_code != 200:
            logging.warning(f"抓取失败 {url}: HTTP {response.status_code}")
            return None

        try:
            html_content = response.text
        except Exception:
            # 如果自动解码失败，尝试强制解码
            html_content = response.content.decode('utf-8', errors='ignore')

        # 提取正文 HTML
        doc = Document(html_content)
        page_title = doc.title()
        summary_html = doc.summary() 

        # 预清洗
        soup = BeautifulSoup(summary_html, 'html.parser')
        
        # 移除显而易见的垃圾
        for tag in soup(['sup', 'script', 'style', 'iframe', 'noscript', 'form', 'button', 'input', 'nav', 'footer', 'aside']):
            tag.decompose()

        # 转 Markdown
        content_md = md(str(soup), heading_style="ATX", strip=['img', 'a'])

        # 后处理与验证
        content_md = re.sub(r'\n{3,}', '\n\n', content_md).strip()
        
        # 防止 JS 渲染页面导致内容为空
        if len(content_md) < 50:
            logging.warning(f"页面 {url} 提取内容过短({len(content_md)} chars)，可能是纯JS渲染，放弃增强。")
            return None

        full_content = f"# {page_title}\n\n{content_md}"
        return full_content

    except Exception as e:
        # 仅记录警告，不阻断主流程
        logging.warning(f"解析页面 {url} 时发生错误: {e}")
        return None