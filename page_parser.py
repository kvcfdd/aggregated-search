# page_parser.py
import logging
import re
from bs4 import BeautifulSoup
from readability import Document
from markdownify import markdownify as md
from http_clients import get_cffi_session

def clean_html_and_to_md(html_content: str) -> str:
    if not html_content:
        return ""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # 移除不必要的标签
        tags_to_remove = [
            'script', 'style', 'iframe', 'noscript', 
            'form', 'button', 'input', 
            'nav', 'footer', 'aside', 'header', 'menu',
            'sup', 'meta', 'link', 'applet', 'object'
        ]
        
        for tag in soup(tags_to_remove):
            tag.decompose()

        # 转 Markdown
        content_md = md(str(soup), heading_style="ATX", strip=['img', 'a'])

        # 移除多余的连续换行
        content_md = re.sub(r'\n{3,}', '\n\n', content_md).strip()
        
        return content_md
    except Exception as e:
        logging.error(f"HTML 转 Markdown 失败: {e}")
        return ""

async def fetch_and_clean_page_content(url: str, referer: str | None = None) -> str | None:
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

        # 解码内容
        try:
            html_content = response.text
        except Exception:
            # 如果自动解码失败，尝试强制解码
            html_content = response.content.decode('utf-8', errors='ignore')

        if not html_content:
            return None

        # 初始化 Readability
        doc = Document(html_content)
        page_title = doc.title()

        # 尝试提取核心正文
        content_md = ""
        try:
            summary_html = doc.summary()
            if summary_html and "<body></body>" not in summary_html:
                content_md = clean_html_and_to_md(summary_html)
        except Exception as e:
            logging.warning(f"Readability 提取出错，准备回退: {e}")

        # 全文回退
        if len(content_md) < 50:
            logging.info(f"Readability 结果过短 ({len(content_md)} chars)，启用全文回退模式: {url}")

            fallback_md = clean_html_and_to_md(html_content)

            if len(fallback_md) > len(content_md):
                content_md = fallback_md

        # 防止 JS 渲染页面导致内容为空
        if len(content_md) < 50:
            logging.warning(f"页面 {url} 最终提取内容过短({len(content_md)} chars)，可能是纯JS渲染，放弃。")
            return None

        full_content = f"# {page_title}\n\n{content_md}"
        return full_content

    except Exception as e:
        # 仅记录警告，不阻断主流程
        logging.warning(f"解析页面 {url} 时发生错误: {e}")
        return None