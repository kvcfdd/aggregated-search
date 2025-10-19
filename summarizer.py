# summarizer.py
import httpx
from config import settings
import logging
import re
from datetime import datetime, timezone
from http_clients import get_httpx_client

GEMINI_API_BASE_URL = settings.GEMINI_REVERSE_PROXY or "https://generativelanguage.googleapis.com"
logging.info(f"Using Gemini API Base URL: {GEMINI_API_BASE_URL}")

def clean_text(text: str) -> str:
    """清理文本中的多余空白字符"""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

async def generate_summary(query: str, search_results: list[dict]) -> str:
    if not settings.GOOGLE_API_KEY or "default" in settings.GOOGLE_API_KEY:
        return "AI summarizer is not configured. Please provide a GOOGLE_API_KEY."

    model_name = "gemini-2.0-flash"
    api_url = f"{GEMINI_API_BASE_URL}/v1beta/models/{model_name}:generateContent"
    
    context = ""
    for i, result in enumerate(search_results[:10], 1):
        title = clean_text(result.get('title', ''))
        snippet = clean_text(result.get('snippet', ''))
        if title and snippet:
            context += f"Source [{i}]:\nTitle: {title}\nSnippet: {snippet}\n\n"

    if not context:
        return "No valid search results found to generate a summary."

    current_time_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    prompt = (
        f"当前日期和时间 (用于判断内容时效性): {current_time_utc}\n\n"
        "请使用中文给提供的内容进行信息融合,过滤无用信息,直接输出,不要加开头,注意细节完整度。\n\n"
        f"USER'S QUERY: \"{query}\"\n\n"
        "--- 原始内容 ---\n"
        f"{context}"
        "--- END OF SEARCH RESULTS ---\n\n"
        "SYNTHESIZED SUMMARY:"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 8192},
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    headers = {'Content-Type': 'application/json'}
    params = {'key': settings.GOOGLE_API_KEY}

    client = get_httpx_client()

    for attempt in range(2):
        try:
            # 使用全局客户端
            response = await client.post(api_url, headers=headers, params=params, json=payload)
            response.raise_for_status()

            response_data = response.json()
            if isinstance(response_data, dict):
                candidates = response_data.get('candidates', [])
                if candidates and isinstance(candidates, list):
                    first_candidate = candidates[0]
                    content = first_candidate.get('content', {})
                    if content and isinstance(content, dict):
                        parts = content.get('parts', [])
                        if parts and isinstance(parts, list) and parts[0].get('text'):
                            return parts[0]['text'].strip()
                if 'text' in response_data and isinstance(response_data['text'], str):
                    return response_data['text'].strip()
            logging.warning(f"Gemini response structure was unexpected: {response_data}")
            return "AI摘要器返回了意外的格式。"

        except httpx.HTTPStatusError as e:
            status = getattr(e.response, 'status_code', None)
            body = e.response.text if e.response else "No response body"
            logging.error(f"HTTP error from Gemini API ({api_url}): {status} - {body}")
            if status and 500 <= status < 600 and attempt == 0:
                continue
            return f"与AI摘要器通信时发生HTTP错误: {status}"
        except Exception as e:
            logging.error(f"Critical error in direct Gemini call ({api_url}) for query '{query}': {e}", exc_info=True)
            if attempt == 0:
                continue
            return f"与AI摘要器通信时发生严重错误: {e}"