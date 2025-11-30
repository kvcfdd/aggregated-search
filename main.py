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
    """
    单源结果预处理：将标题包含关键词的结果前置，优化后续排名权重。
    """
    if not results:
        return []
    
    keyword_lower = keyword.strip().lower()
    if not keyword_lower:
        return results
        
    high_priority = []
    low_priority = []
    
    for item in results:
        title = str(item.get('title', '')).lower()
        if keyword_lower in title:
            high_priority.append(item)
        else:
            low_priority.append(item)
            
    return high_priority + low_priority

def reciprocal_rank_fusion(providers_results: list[list[dict]], k: int = 60) -> list[dict]:
    """
    使用倒数排名融合 (RRF) 算法合并结果。
    RRF score = sum(1 / (k + rank))
    如果同一个链接出现在多个源中，分数会叠加，从而提升排名。
    针对被标记为 'penalized' (黑名单降权) 的条目，分数乘以惩罚系数。
    """
    fused_scores = {}
    items_map = {}
    
    # 记录已处理的标题，防止不同URL但内容完全相同的情况
    seen_titles = set()

    for result_list in providers_results:
        for rank, item in enumerate(result_list):
            link = item.get('link')
            title = item.get('title') or ""
            is_penalized = item.get('_is_penalized', False)
            
            if not link:
                continue

            # URL 标准化去重
            dedupe_key = get_base_url_for_dedupe(link)
            clean_title = title.strip().lower()

            # 标题完全匹配去重
            # 防止不同参数的URL指向同一篇文章导致刷屏
            if clean_title in seen_titles and dedupe_key not in items_map:
                continue

            if dedupe_key not in fused_scores:
                fused_scores[dedupe_key] = 0.0
                items_map[dedupe_key] = item
                seen_titles.add(clean_title)
            
            # 基础分数
            score = 1 / (k + rank + 1)
            
            # 如果是黑名单条目，应用惩罚 (乘以 0.1)
            if is_penalized:
                score *= 0.1

            fused_scores[dedupe_key] += score

    # 根据分数降序排序
    sorted_keys = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
    
    return [items_map[key] for key in sorted_keys]

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
                        "url": original_url,
                        "source": item.get("source")
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
        tasks = [
            text_ddg.search_ddg(q, settings.PER_PROVIDER_FETCH_TEXT),
            text_bing.search_bing(q, settings.PER_PROVIDER_FETCH_TEXT),
            text_baidu.search_baidu(q, settings.PER_PROVIDER_FETCH_TEXT)
        ]
        raw_results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # 预编译黑名单
        domain_blacklist = {domain.strip() for domain in settings.DOMAIN_BLACKLIST.split(',') if domain.strip()}
        title_blacklist = {kw.strip().lower() for kw in settings.TITLE_BLACKLIST.split(',') if kw.strip()}
        
        # 获取小写查询词
        q_lower = q.strip().lower()

        cleaned_providers_lists = []

        # 清洗、标记黑名单、关键词优先
        for result_list in raw_results_list:
            if isinstance(result_list, Exception):
                logging.warning(f"A search provider failed: {result_list}")
                continue
            
            if not result_list:
                continue

            filtered_list = []
            for item in result_list:
                link = item.get('link')
                title = item.get('title') or ""
                snippet = item.get('snippet')

                # 基础字段校验
                if not all([link, title, snippet]):
                    continue
                
                # 初始化降权标记
                is_penalized = False

                # 域名黑名单判定
                if domain_blacklist:
                    try:
                        domain = urlparse(link).netloc.lower()
                        if domain:
                            if any(bd in domain and bd not in q_lower for bd in domain_blacklist):
                                is_penalized = True
                    except Exception:
                        pass
                
                # 标题黑名单判定
                if not is_penalized and title_blacklist:
                    title_lower = title.lower()
                    if any(kw in title_lower and kw not in q_lower for kw in title_blacklist):
                        is_penalized = True
                
                # 写入标记，不删除条目
                item['_is_penalized'] = is_penalized
                filtered_list.append(item)
            
            # 单源内部重排 包含搜索词的标题优先
            prioritized_list = prioritize_results_with_keyword(filtered_list, q)
            if prioritized_list:
                cleaned_providers_lists.append(prioritized_list)

        if not cleaned_providers_lists:
            response_payload = StandardResponse(
                code=404,
                message=f"No search results found for the query: '{q}'",
                data=None
            )
            return JSONResponse(status_code=404, content=response_payload.model_dump())

        # 使用 RRF 算法融合多个源
        final_ranked_results = reciprocal_rank_fusion(cleaned_providers_lists)

        # 截取最终结果
        final_results = final_ranked_results[:limit]
        
        # 格式化输出
        output_data = []
        for result in final_results:
            output_data.append({
                "title": result.get('title'),
                "url": result.get('link'),
                "description": result.get('snippet')
            })

        response_payload = StandardResponse(
            code=200, message="OK",
            data={"results": output_data}
        )
        return JSONResponse(content=response_payload.model_dump())

@app.get("/", include_in_schema=False)
def read_root():
    return {"message": "Welcome to the aggregated-search API. Go to /docs for API documentation."}
