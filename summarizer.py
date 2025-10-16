# summarizer.py
import httpx
from config import settings
import logging
import re

GEMINI_API_BASE_URL = settings.GEMINI_REVERSE_PROXY or "https://generativelanguage.googleapis.com"
logging.info(f"Using Gemini API Base URL: {GEMINI_API_BASE_URL}")


def clean_text(text: str) -> str:
    """A simple function to clean text."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


async def generate_summary(query: str, search_results: list[dict]) -> str:
    """
    Generates a summary by directly calling the Gemini REST API via a configurable URL.
    """
    if not settings.GOOGLE_API_KEY or "default" in settings.GOOGLE_API_KEY:
        return "AI summarizer is not configured. Please provide a GOOGLE_API_KEY."

    model_name = "gemini-2.0-flash"
    api_url = f"{GEMINI_API_BASE_URL}/v1beta/models/{model_name}:generateContent"
    
    context = ""
    for i, result in enumerate(search_results[:8], 1):
        title = clean_text(result.get('title', ''))
        snippet = clean_text(result.get('snippet', ''))
        if title and snippet:
            context += f"Source [{i}]:\nTitle: {title}\nSnippet: {snippet}\n\n"

    if not context:
        return "No valid search results found to generate a summary."

    prompt = (
        "请使用中文给提供的内容进行信息融合,直接输出,不要加开头,注意细节完整度。\n\n"
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

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, headers=headers, params=params, json=payload)
            response.raise_for_status()

        response_data = response.json()
        
        # 解析响应
        if 'candidates' in response_data and response_data['candidates']:
            first_candidate = response_data['candidates'][0]
            if 'content' in first_candidate and 'parts' in first_candidate['content'] and first_candidate['content']['parts']:
                return first_candidate['content']['parts'][0].get('text', '').strip()
        
        logging.warning(f"Gemini response structure was unexpected: {response_data}")
        return "AI摘要器返回了意外的格式。"

    except httpx.HTTPStatusError as e:
        logging.error(f"HTTP error from Gemini API ({api_url}): {e.response.status_code} - {e.response.text}")
        return f"与AI摘要器通信时发生HTTP错误: {e.response.status_code}"
    except Exception as e:
        logging.error(f"Critical error in direct Gemini call ({api_url}) for query '{query}': {e}")
        return f"与AI摘要器通信时发生严重错误: {e}"