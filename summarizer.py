# summarizer.py
import httpx
from config import settings
import logging
import re
from datetime import datetime, timezone

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
    # 选取前 10 个最相关的结果构建上下文
    for i, result in enumerate(search_results[:10], 1):
        title = clean_text(result.get('title', ''))
        snippet = clean_text(result.get('snippet', ''))
        if title and snippet:
            context += f"Source [{i}]:\nTitle: {title}\nSnippet: {snippet}\n\n"

    if not context:
        return "No valid search results found to generate a summary."

    # 提供当前UTC时间，帮助模型判断信息的时效性
    current_time_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    prompt = (
        f"当前日期和时间 (用于判断内容时效性): {current_time_utc}\n\n"
        "请使用中文给提供的内容进行信息融合,直接输出,不要加开头,注意细节完整度。\n\n"
        f"USER'S QUERY: \"{query}\"\n\n"
        "--- 原始内容 ---\n"
        f"{context}"
        "--- END OF SEARCH RESULTS ---\n\n"
        "SYNTHESIZED SUMMARY:"
    )

    # 构建 Gemini API 请求
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 8192},
        # 关闭所有安全审查
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    headers = {'Content-Type': 'application/json'}
    params = {'key': settings.GOOGLE_API_KEY}

    # 实现简单的重试机制，以应对临时的网络波动或服务器端 5xx 错误
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(api_url, headers=headers, params=params, json=payload)
                response.raise_for_status()

            response_data = response.json()

            # 兼容官方和一些反向代理可能存在的不同响应结构
            # 常见结构: {"candidates": [{"content": {"parts": [{"text": ...}]}}]}
            if isinstance(response_data, dict):
                candidates = response_data.get('candidates', [])
                if candidates and isinstance(candidates, list):
                    first_candidate = candidates[0]
                    content = first_candidate.get('content', {})
                    if content and isinstance(content, dict):
                        parts = content.get('parts', [])
                        if parts and isinstance(parts, list) and parts[0].get('text'):
                            return parts[0]['text'].strip()

                # 兼容一些直接返回 text 的简化版代理
                if 'text' in response_data and isinstance(response_data['text'], str):
                    return response_data['text'].strip()

            logging.warning(f"Gemini response structure was unexpected: {response_data}")
            return "AI摘要器返回了意外的格式。"

        except httpx.HTTPStatusError as e:
            status = getattr(e.response, 'status_code', None)
            body = e.response.text if e.response else "No response body"
            logging.error(f"HTTP error from Gemini API ({api_url}): {status} - {body}")
            # 仅对 5xx 系列服务器错误进行重试
            if status and 500 <= status < 600 and attempt == 0:
                continue
            return f"与AI摘要器通信时发生HTTP错误: {status}"
        except Exception as e:
            logging.error(f"Critical error in direct Gemini call ({api_url}) for query '{query}': {e}", exc_info=True)
            # 对其他未知异常（如网络超时）也重试一次
            if attempt == 0:
                continue
            return f"与AI摘要器通信时发生严重错误: {e}"