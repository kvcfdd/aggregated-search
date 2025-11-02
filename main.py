# main.py
import jieba
import asyncio
import logging
import math
import re
import random
from contextlib import asynccontextmanager
from typing import Literal
from urllib.parse import urlparse, urlunparse, parse_qsl

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from httpx import AsyncClient
from curl_cffi.requests import AsyncSession
import http_clients

from config import settings
from search_providers import text_ddg, text_bing, text_baidu, image_serpapi, image_bing, image_pixiv, image_yandex, image_dimtown
from summarizer import generate_summary
from page_parser import fetch_baike_content, fetch_and_clean_page_content

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
    description="一个聚合多个搜索源、进行智能排序去重并提供AI摘要的API服务。",
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

def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        path = parsed.path or ''
        # 过滤掉常见的点击跟踪参数
        query_pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                       if not k.lower().startswith('utm_') and k.lower() not in ('gclid', 'fbclid')]
        query = '&'.join([f"{k}={v}" for k, v in query_pairs])
        netloc = parsed.netloc.lower()
        normalized = urlunparse((parsed.scheme, netloc, path, '', query, ''))
        return normalized
    except Exception:
        # 如果解析失败，返回原始URL的小写形式作为兜底
        return url.strip().lower()


def tokenize(text: str) -> list[str]:
    """使用 jieba 进行中英文混合分词"""
    tokens = jieba.cut_for_search(text)
    return [t.lower() for t in tokens if len(t.strip()) > 1]


def compute_bm25_scores(items: list[dict], query: str, k1: float | None = None, b: float | None = None) -> list[tuple[float, dict]]:
    docs = [(item.get('title', ''), item.get('snippet', '')) for item in items]

    N = len(docs)
    doc_tokens, df, doc_lens = [], {}, []
    
    # 预处理：分词、计算文档长度和词频
    for title, snippet in docs:
        # 为标题中的词赋予更高权重（此处简单地将标题分词重复一次）
        title_toks = tokenize(title)
        snippet_toks = tokenize(snippet)
        tokens = title_toks * 2 + snippet_toks
        
        doc_lens.append(len(tokens) or 1)
        unique_tokens = set(tokens)
        for t in unique_tokens:
            df[t] = df.get(t, 0) + 1
        doc_tokens.append(tokens)

    avgdl = sum(doc_lens) / len(doc_lens) if doc_lens else 1.0

    # 从配置加载 BM25
    k1 = k1 if k1 is not None else settings.BM25_K1
    b = b if b is not None else settings.BM25_B
    q_terms = tokenize(query)

    penalty_keywords = {
        kw.strip().lower() 
        for kw in settings.TITLE_PENALTY_KEYWORDS.split(',') 
        if kw.strip()
    }
    penalty_value = settings.TITLE_PENALTY_VALUE

    scores = []

    # 计算每个文档的分数
    for tokens, item, doc_len in zip(doc_tokens, items, doc_lens):
        score = 0.0
        for q in q_terms:
            if q not in df:
                continue
            
            # 使用对数形式计算 IDF，数值更稳定
            idf = math.log(1 + (N - df[q] + 0.5) / (df[q] + 0.5))
            
            # 计算词频 TF
            tf = tokens.count(q)
            
            # BM25核心公式
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_len / avgdl))
            tf_component = numerator / denominator if denominator > 0 else 0.0
            
            score += idf * tf_component
            
        # 如果查询词出现在URL中，给予少量加分
        url = (item.get('link') or '').lower()
        for q_term in q_terms:
            if q_term in url:
                score += 0.5
        if penalty_keywords:
            title = item.get('title', '').lower()
            for keyword in penalty_keywords:
                if keyword in title:
                    score -= penalty_value
                    break
        scores.append((score, item))

    return scores


def jaccard_similarity(a: set, b: set) -> float:
    """去重"""
    if not a or not b:
        return 0.0
    intersection_len = len(a.intersection(b))
    union_len = len(a.union(b))
    return intersection_len / union_len


def content_dedupe(items: list[dict], threshold: float | None = None) -> list[dict]:
    threshold = threshold if threshold is not None else settings.CONTENT_DEDUPE_THRESHOLD
    kept_items = []
    seen_token_sets = []
    for item in items:
        text = ((item.get('title') or '') + ' ' + (item.get('snippet') or '')).lower()
        tokens = set(tokenize(text))
        is_duplicate = False
        for seen_set in seen_token_sets:
            if jaccard_similarity(seen_set, tokens) >= threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            kept_items.append(item)
            seen_token_sets.append(tokens)
    return kept_items

@app.get("/search",
         summary="执行聚合搜索，优先返回AI摘要",
         response_model=StandardResponse,
         description=("执行文本或图片搜索。对于文本搜索，服务会聚合、排序、去重多个来源的结果，"
                      "并优先尝试生成AI摘要。如果摘要失败，则返回处理后的搜索结果列表。")
)
async def search(
    q: str = Query(..., description="搜索查询词。"),
    type: Literal['Information', 'image'] = Query('Information', description="搜索类型：'Information' 或 'image'。"),
    limit: int = Query(10, ge=1, le=100, description="最终返回的结果数量上限。"),
    enhance: bool = Query(False, description="是否进行内容增强。如果结果中存在百度百科，则优先增强；否则，尝试增强排名第一的结果。此过程会增加响应时间。")
):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty.")

    if type == 'image':
        tasks = [
            image_serpapi.search_images_serpapi(q, settings.PER_PROVIDER_FETCH_IMAGE),
            image_bing.search_bing_images(q, settings.PER_PROVIDER_FETCH_IMAGE),
            image_pixiv.search_pixiv_images(q, settings.PER_PROVIDER_FETCH_IMAGE),
            image_yandex.search_yandex_images(q, settings.PER_PROVIDER_FETCH_IMAGE),
            image_dimtown.search_dimtown_images(q, settings.PER_PROVIDER_FETCH_IMAGE),
        ]
        
        results_from_providers = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_images, seen_originals = [], set()
        query_lower = q.lower()
        for result_list in results_from_providers:
            if isinstance(result_list, Exception):
                logging.warning(f"An image search provider failed: {result_list}")
                continue
            
            for item in result_list:
                original_url = item.get('original')
                title = item.get("title") or ""
                if original_url and original_url not in seen_originals and query_lower in title.lower():
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
        tasks = [
            text_ddg.search_ddg(q, settings.PER_PROVIDER_FETCH_TEXT),
            text_bing.search_bing(q, settings.PER_PROVIDER_FETCH_TEXT),
            text_baidu.search_baidu(q, settings.PER_PROVIDER_FETCH_TEXT)
        ]
        results_from_providers = await asyncio.gather(*tasks, return_exceptions=True)

        blacklist = {domain.strip() for domain in settings.DOMAIN_BLACKLIST.split(',') if domain.strip()}

        all_results, seen_links = [], set()
        for result_list in results_from_providers:
            if isinstance(result_list, Exception):
                logging.warning(f"A search provider failed: {result_list}")
                continue
            for item in result_list:
                link = item.get('link')
                # 过滤无效结果
                if not all([link, item.get('title'), item.get('snippet')]):
                    continue

                # 检查域名是否在黑名单中
                if blacklist:
                    try:
                        domain = urlparse(link).netloc.lower()
                        if domain and any(blacklisted_domain in domain for blacklisted_domain in blacklist):
                            logging.info(f"已根据本地配置的黑名单过滤结果: {link}")
                            continue
                    except Exception as e:
                        logging.debug(f"无法为黑名单检查解析域名 {link}: {e}")
                
                # 链接去重
                if link in seen_links:
                    continue
                seen_links.add(link)
                all_results.append(item)
        
        if not all_results:
            response_payload = StandardResponse(
                code=404,
                message=f"No search results found for the query: '{q}'",
                data=None
            )
            return JSONResponse(status_code=404, content=response_payload.model_dump())

        # BM25-like 智能排序
        scored_results = compute_bm25_scores(all_results, q)
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # 规范化URL去重
        deduped_by_url, normalized_seen = [], set()
        for score, item in scored_results:
            normalized = normalize_url(item.get('link', ''))
            if not normalized or normalized in normalized_seen:
                continue
            normalized_seen.add(normalized)
            deduped_by_url.append(item)

        baike_items = [item for item in deduped_by_url if "baike.baidu.com" in item.get('link', '')]
        other_items = [item for item in deduped_by_url if "baike.baidu.com" not in item.get('link', '')]
        # 重新组合列表，百科来源的在最前面
        deduped_by_url = baike_items + other_items

        if enhance and deduped_by_url:
            item_to_enhance = None
            task_to_run = None
            if baike_items:
                item_to_enhance = baike_items[0]
                link = item_to_enhance.get('link', '')
                task_to_run = fetch_baike_content(link)
                logging.info(f"增强模式: 发现百科链接，尝试抓取 {link}")
            else:
                item_to_enhance = deduped_by_url[0]
                link = item_to_enhance.get('link', '')
                task_to_run = fetch_and_clean_page_content(link)
                logging.info(f"增强模式: 未发现百科链接，尝试对首个结果进行深度请求: {link}")

            if task_to_run and item_to_enhance:
                enhanced_content = await task_to_run
                if enhanced_content:
                    original_snippet = item_to_enhance.get('snippet', '')
                    item_to_enhance['snippet'] = enhanced_content
                    logging.info(f"成功增强结果。内容长度从 {len(original_snippet)} 变为 {len(enhanced_content)}。")
                else:
                    logging.warning(f"增强任务未能从 {item_to_enhance.get('link')} 获取到内容。")

        # 尝试生成AI摘要
        summary_result = None
        try:
            # 将排序后最相关的结果传给摘要器
            summary_result = await generate_summary(q, deduped_by_url)
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
                   # "query": q,
                    "results": summary_data.model_dump()
                }
            )
            return JSONResponse(content=response_payload.model_dump())
        else:
            logging.warning(f"Summarization failed for query: '{q}'. Falling back to raw results. Reason: {summary_result}")

            # 内容去重和最终裁剪
            content_filtered_results = content_dedupe(deduped_by_url)
            final_results = content_filtered_results[:limit]
            
            i_data = []
            for i, result in enumerate(final_results, 1):
                i_data.append({
                   # "source": i,
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