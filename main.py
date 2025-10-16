# main.py
import asyncio
import logging
from typing import Literal

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from search_providers import text_ddg, text_bing, image_serpapi
from summarizer import generate_summary

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(
    title="Intelligent Search API"
)

class TextSearchResponse(BaseModel):
    query: str
    status: Literal['success', 'fallback', 'error']
    content: str

class ImageSearchResult(BaseModel):
    title: str | None
    source: str | None
    link: str | None
    original: str
    thumbnail: str

class ImageSearchResponse(BaseModel):
    query: str
    images: list[ImageSearchResult]

SUMMARY_FAILURE_PREFIXES = [
    "AI summarizer is not configured",
    "AI摘要器未能为此查询生成响应",
    "与AI摘要器通信时发生严重错误",
    "No valid search results found",
]

@app.get("/search",
         summary="Get a structured summary or raw results as a fallback",
         description="For type='text', returns a JSON object with a status and content. 'status: success' means content is an AI summary. 'status: fallback' means content is concatenated raw search results. For type='image', returns a JSON object of images."
)
async def search(
    q: str = Query(..., description="The search query."),
    type: Literal['text', 'image'] = Query('text', description="Specify 'text' or 'image' search."),
    limit: int = Query(10, ge=1, le=30, description="The maximum number of search results to fetch.")
):
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty.")

    if type == 'image':
        loop = asyncio.get_running_loop()
        image_results_list = await loop.run_in_executor(
            None, image_serpapi.search_images_serpapi, q, limit * 2
        )
        all_images = []
        seen_originals = set()
        for item in image_results_list:
            if item.get('original') and item['original'] not in seen_originals:
                all_images.append(ImageSearchResult(**item))
                seen_originals.add(item['original'])
        final_images = all_images[:limit]
        response_data = ImageSearchResponse(query=q, images=final_images)
        return JSONResponse(content=response_data.model_dump())

    elif type == 'text':
        tasks = [text_ddg.search_ddg(q, limit), text_bing.search_bing(q, limit)]
        results_from_providers = await asyncio.gather(*tasks, return_exceptions=True)

        all_results = []
        seen_links = set()
        for result_list in results_from_providers:
            if isinstance(result_list, Exception):
                logging.error(f"A search provider failed: {result_list}")
                continue
            for item in result_list:
                if item.get('link') and item.get('title') and item.get('snippet'):
                    all_results.append(item)
                    seen_links.add(item['link'])
        
        if not all_results:
            return JSONResponse(
                status_code=404,
                content=TextSearchResponse(
                    query=q,
                    status='error',
                    content=f"No search results found for the query: '{q}'"
                ).model_dump()
            )

        summary_text = None
        try:
            summary_text = await generate_summary(q, all_results)
        except Exception as e:
            logging.error(f"Summarization process threw an exception: {e}")
            summary_text = f"Summarization process failed with an exception: {e}"

        is_summary_successful = (
            summary_text and 
            not any(summary_text.startswith(prefix) for prefix in SUMMARY_FAILURE_PREFIXES)
        )

        if is_summary_successful:
            logging.info(f"Successfully generated summary for query: '{q}'")
            response_data = TextSearchResponse(
                query=q,
                status='success',
                content=summary_text
            )
            return JSONResponse(content=response_data.model_dump())
        else:
            logging.warning(f"Summarization failed for query: '{q}'. Falling back to raw text. Reason: {summary_text}")

            fallback_parts = []
            for i, result in enumerate(all_results, 1):
                fallback_parts.append(f"Source [{i}]:\nTitle: {result['title']}\nSnippet: {result['snippet']}\nURL: {result['link']}")
            
            fallback_text = "\n\n".join(fallback_parts)
            response_data = TextSearchResponse(
                query=q,
                status='fallback',
                content=fallback_text
            )
            return JSONResponse(content=response_data.model_dump())

@app.get("/")
def read_root():
    return {"message": "Welcome to the Intelligent Search API. Go to /docs for API documentation."}