# http_clients.py
from typing import Optional
from httpx import AsyncClient
from curl_cffi.requests import AsyncSession

httpx_client: Optional[AsyncClient] = None
cffi_session: Optional[AsyncSession] = None

def get_httpx_client() -> AsyncClient:
    """
    获取全局共享的 httpx.AsyncClient 实例。

    Raises:
        RuntimeError: 如果客户端实例尚未被初始化。

    Returns:
        AsyncClient: 全局共享的 httpx 客户端实例。
    """
    if httpx_client is None:
        raise RuntimeError(
            "HTTPX client is not initialized. "
            "The application lifespan event probably failed."
        )
    return httpx_client

def get_cffi_session() -> AsyncSession:
    """
    获取全局共享的 curl_cffi.requests.AsyncSession 实例。

    Raises:
        RuntimeError: 如果会话实例尚未被初始化。

    Returns:
        AsyncSession: 全局共享的 curl_cffi 会话实例。
    """
    if cffi_session is None:
        raise RuntimeError(
            "CFFI session is not initialized. "
            "The application lifespan event probably failed."
        )
    return cffi_session