# main.py
import asyncio
import logging
import random
from contextlib import asynccontextmanager
from typing import Literal
from urllib.parse import urlparse, urlunparse

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from httpx import AsyncClient
from curl_cffi.requests import AsyncSession
import http_clients

from config import settings
from search_providers import text_ddg, text_bing, text_baidu, image_serpapi, image_bing, image_pixiv, image_yandex, image_dimtown, image_acg66 
from summarizer import generate_summary
from page_parser import fetch_and_clean_page_content

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Application startup: Initializing HTTP clients...")
    # 实例化全局客户端
    http_clients.httpx_client = AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        },
        follow_redirects=True,
        timeout=15  # 超时
    )
    http_clients.cffi_session = AsyncSession(
        impersonate="chrome120",
        timeout=20  # 超时
    )
    logging.info("HTTP clients initialized successfully.")

    yield

    logging.info("Application shutdown: Closing HTTP clients...")
    if http_clients.httpx_client:
        await http_clients.httpx_client.aclose()
    if http_clients.cffi_session:
        await http_clients.cffi_session.close()
    logging.info("HTTP clients closed gracefully.")


app = FastAPI(
    title="aggregated search API",
    description="一个聚合多个搜索源的API服务。",
    lifespan=lifespan
)

class StandardResponse(BaseModel):
    code: int
    message: str
    data: dict | list | None = None

class ImageSearchResult(BaseModel):
    title: str | None
    source: str | None
    url: str | None

class Source(BaseModel):
    id: int
    title: str | None
    url: str | None

class SummaryResult(BaseModel):
    summary: str
    sources: list[Source]

# 定义摘要失败的标志性前缀，用于回退判断
SUMMARY_FAILURE_PREFIXES = [
    "AI summarizer is not configured",
    "AI摘要器未能为此查询生成响应",
    "与AI摘要器通信时发生严重错误",
    "No valid search results found",
    "与AI摘要器通信时发生HTTP错误",
    "AI摘要器返回了意外的格式",
]

def get_base_url_for_dedupe(url: str) -> str:
    try:
        parsed = urlparse(url)
        # 转换为小写 netloc 以忽略大小写差异
        netloc = parsed.netloc.lower()
        # 重组URL，Query和Fragment置空
        clean_url = urlunparse((parsed.scheme, netloc, parsed.path, '', '', ''))
        return clean_url.strip()
    except Exception:
        return url.strip().lower()

def prioritize_results_with_keyword(results: list[dict], keyword: str) -> list[dict]:
    if not results:
        return []
    
    keyword_lower = keyword.strip().lower()
    if not keyword_lower:
        return results
        
    high_priority = []
    low_priority = []
    
    for item in results:
        title = str(item.get('title', '')).lower()
        # 简单包含匹配
        if keyword_lower in title:
            high_priority.append(item)
        else:
            low_priority.append(item)
            
    return high_priority + low_priority

def interleave_results(providers_results: list[list[dict]]) -> list[dict]:
    """
    混合排序：轮询各个源的结果。
    """
    mixed = []
    # 获取最长的结果列表长度
    max_len = max((len(r) for r in providers_results), default=0)
    
    for i in range(max_len):
        for res_list in providers_results:
            if i < len(res_list):
                mixed.append(res_list[i])
    return mixed

@app.get("/search",
         summary="聚合搜索接口",
         response_model=StandardResponse,
         description=("执行聚合搜索，支持信息和图片两种类型。")
)
async def search(
    q: str = Query(..., description="搜索查询词。"),
    type: Literal['Information', 'image'] = Query('Information', description="搜索类型：'Information' 或 'image'。"),
    limit: int = Query(10, ge=1, le=100, description="返回结果数量上限，范围1-100。")
):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty.")

    if type == 'image':
        tasks = [
            image_serpapi.search_images_serpapi(q, settings.PER_PROVIDER_FETCH_IMAGE),
            image_bing.search_bing_images(q, settings.PER_PROVIDER_FETCH_IMAGE),
            image_yandex.search_yandex_images(q, settings.PER_PROVIDER_FETCH_IMAGE),
            image_dimtown.search_dimtown_images(q, settings.PER_PROVIDER_FETCH_IMAGE),
            image_pixiv.search_pixiv_images(q, settings.PER_PROVIDER_FETCH_IMAGE),
            image_acg66.search_acg66_images(q, settings.PER_PROVIDER_FETCH_IMAGE),
        ]
        
        results_from_providers = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_images, seen_originals = [], set()
        for result_list in results_from_providers:
            if isinstance(result_list, Exception):
                logging.warning(f"An image search provider failed: {result_list}")
                continue
            
            for item in result_list:
                original_url = item.get('original')
                title = item.get("title") or ""
                if original_url and original_url not in seen_originals:
                    image_data = {
                        "title": title,
                        "source": item.get("source"),
                        "url": original_url
                    }
                    all_images.append(ImageSearchResult(**image_data))
                    seen_originals.add(original_url)

        random.shuffle(all_images)
        final_images = all_images[:limit]
        response_payload = StandardResponse(
            code=200, message="OK",
            data={"images": [img.model_dump() for img in final_images]}
        )
        return JSONResponse(content=response_payload.model_dump())

    elif type == 'Information':
        NUM_TO_ENHANCE = 1 # 固定深度解析排名最前的3条结果

        tasks = [
            text_ddg.search_ddg(q, settings.PER_PROVIDER_FETCH_TEXT),
            text_bing.search_bing(q, settings.PER_PROVIDER_FETCH_TEXT),
            text_baidu.search_baidu(q, settings.PER_PROVIDER_FETCH_TEXT)
        ]
        raw_results_list = await asyncio.gather(*tasks, return_exceptions=True)

        valid_provider_results = []
        for result_list in raw_results_list:
            if isinstance(result_list, Exception):
                logging.warning(f"A search provider failed: {result_list}")
                continue
            if result_list:
                # 单源重排：先将当前源中包含关键词的结果排在前面
                prioritized_list = prioritize_results_with_keyword(result_list, q)
                valid_provider_results.append(prioritized_list)

        if not valid_provider_results:
            response_payload = StandardResponse(
                code=404,
                message=f"No search results found for the query: '{q}'",
                data=None
            )
            return JSONResponse(status_code=404, content=response_payload.model_dump())

        # 混合排序
        interleaved_results = interleave_results(valid_provider_results)

        # 解析黑名单配置
        domain_blacklist = {domain.strip() for domain in settings.DOMAIN_BLACKLIST.split(',') if domain.strip()}
        title_blacklist = {kw.strip().lower() for kw in settings.TITLE_BLACKLIST.split(',') if kw.strip()}
        
        final_deduped_results = []
        seen_urls = set()
        seen_titles = set()

        # 遍历混合后的结果进行过滤和去重
        for item in interleaved_results:
            link = item.get('link')
            title = item.get('title') or ""
            snippet = item.get('snippet')
            
            # 基础校验
            if not all([link, title, snippet]):
                continue
            
            # 域名黑名单过滤
            if domain_blacklist:
                try:
                    domain = urlparse(link).netloc.lower()
                    if domain and any(blacklisted_domain in domain for blacklisted_domain in domain_blacklist):
                        continue
                except Exception:
                    pass

            # 标题关键词黑名单过滤
            if title_blacklist:
                title_lower = title.lower()
                if any(kw in title_lower for kw in title_blacklist):
                    continue
            
            # URL 去重
            dedupe_url_key = get_base_url_for_dedupe(link)
            if dedupe_url_key in seen_urls:
                continue
            
            # 标题去重
            clean_title = title.strip().lower()
            if clean_title in seen_titles:
                continue

            seen_urls.add(dedupe_url_key)
            seen_titles.add(clean_title)
            final_deduped_results.append(item)

        # 准备进行深度抓取的数据
        items_to_enhance = final_deduped_results[:NUM_TO_ENHANCE]

        if items_to_enhance:
            fetch_tasks = []
            for item in items_to_enhance:
                link = item.get('link', '')
                referer = "https://www.bing.com/"
                if "baidu.com" in link:
                    referer = "https://www.baidu.com/"
                fetch_tasks.append(fetch_and_clean_page_content(link, referer=referer))

            if fetch_tasks: 
                enhanced_contents = await asyncio.gather(*fetch_tasks, return_exceptions=True)
                
                for i, content in enumerate(enhanced_contents):
                    item = items_to_enhance[i]
                    if isinstance(content, Exception):
                        logging.warning(f"深度抓取任务失败 {item.get('link')}: {content}")
                    elif content:
                        original_snippet_len = len(item.get('snippet', ''))
                        item['snippet'] = content
                        logging.info(f"成功增强结果 {item.get('link')}。内容长度从 {original_snippet_len} 变为 {len(content)}。")
                    else:
                        logging.warning(f"深度抓取任务未能从 {item.get('link')} 获取到有效内容。")

        # 尝试生成AI摘要
        summary_result = None
        try:
            # 传递给摘要的数据
            results_for_summary = final_deduped_results[:limit]
            summary_result = await generate_summary(q, results_for_summary)
        except Exception as e:
            logging.error(f"Summarization process threw a critical exception: {e}", exc_info=True)
            summary_result = f"Summarization process failed with an exception: {e}"
        
        is_summary_successful = isinstance(summary_result, dict)

        if is_summary_successful:
            logging.info(f"Successfully generated summary with citations for query: '{q}'")
            summary_data = SummaryResult(**summary_result)
            response_payload = StandardResponse(
                code=200, message="OK",
                data={
                    "results": summary_data.model_dump()
                }
            )
            return JSONResponse(content=response_payload.model_dump())
        else:
            logging.warning(f"Summarization failed for query: '{q}'. Falling back to raw results. Reason: {summary_result}")

            # 回退：直接返回列表
            final_results = final_deduped_results[:limit]
            
            i_data = []
            for i, result in enumerate(final_results, 1):
                i_data.append({
                    "title": result.get('title'),
                    "description": result.get('snippet'),
                    "url": result.get('link')
                })

            response_payload = StandardResponse(
                code=200, message="OK",
                data={"results": i_data}
            )
            return JSONResponse(content=response_payload.model_dump())

@app.get("/", include_in_schema=False)
def read_root():
    return {"message": "Welcome to the aggregated-search API. Go to /docs for API documentation."}