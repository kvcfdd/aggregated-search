# aggregated-search API

一个轻量级的聚合搜索服务。

### 快速开始

1.  克隆项目并安装依赖：

    ```bash
    git clone https://github.xn--6rtu33f.top/kvcfdd/aggregated-search.git
    cd aggregated-search
    pip install -r requirements.txt
    ```

2.  配置环境：复制 `.env.example` 为 `.env` 文件，并根据需要编辑。

    ```bash
    cp .env.example .env
    ```

3.  运行服务：

    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

### 数据源说明

本服务聚合了以下搜索源：

-   **信息搜索**:
    -   DuckDuckGo
    -   必应 (Bing)
    -   百度 (Baidu)

-   **图片搜索**:
    -   SerpApi (Google Images)
    -   必应图片 (Bing Images)

### API 概览

#### `GET /search`

-   **参数**:
    -   `q` (string, **必需**): 查询词。
    -   `type` (string, 可选): `'text'` 或 `'image'` (默认 `'text'`)。
    -   `limit` (int, 可选): 最终返回结果的条数 (默认 10, 范围 1–100)。
    -   `enhance` (string, 可选): 深入请求(百度百科) `'true'` 或 `'false'` (默认 `'false'`)。

    **enhance** 参数会有额外延迟与性能开销

-   **请求示例**:

    *   **文本搜索**:
        ```bash
        curl -X GET "http://127.0.0.1:8000/search?type=text&q=FastAPI最佳实践"
        ```

    *   **图片搜索**:
        ```bash
        curl -X GET "http://127.0.0.1:8000/search?type=image&q=风景壁纸&limit=50"
        ```

-   **返回示例**:

    *   **文本搜索 - 摘要成功 (`message: "OK"`)**:
        ```json
        {
          "success": true,
          "code": 200,
          "message": "OK",
          "data": {
            "query": "FastAPI最佳实践",
            "summary": "FastAPI 是一个现代、高性能的 Python Web 框架..."
          }
        }
        ```

    *   **文本搜索 - 回退列表 (`message: "fallback"`)**:
        ```json
        {
          "success": true,
          "code": 200,
          "message": "fallback",
          "data": {
            "query": "FastAPI最佳实践",
            "results": [
              {
                "source": 1,
                "title": "FastAPI Best Practices - Real Python",
                "description": "Learn about the best practices for building robust and maintainable APIs with FastAPI...",
                "url": "https://realpython.com/fastapi-best-practices/"
              },
              {
                "source": 2,
                "title": "A Comprehensive Guide to FastAPI Best Practices - ...",
                "description": "Explore dependency injection, testing, project structure, and more to build production-ready FastAPI applications.",
                "url": "https://example.com/fastapi-guide"
              }
            ]
          }
        }
        ```

    *   **图片搜索 - 成功示例 (`type=image`)**:
        ```json
        {
          "success": true,
          "code": 200,
          "message": "OK",
          "data": {
            "query": "风景壁纸",
            "images": [
              {
                "title": "4K高清唯美风景壁纸 - Pexels",
                "source": "pexels.com",
                "link": "https://www.pexels.com/search/landscape/",
                "original": "https://images.pexels.com/photos/12345/landscape.jpeg",
                "thumbnail": "https://tse1.mm.bing.net/th?id=OIP.abc...&pid=15.1"
              },
              {
                "title": "瑞士山脉湖泊风景桌面壁纸",
                "source": "wallpaperhub.app",
                "link": "https://wallpaperhub.app/wallpapers/123",
                "original": "https://wallpaperhub.app/images/swiss-mountains.jpg",
                "thumbnail": "https://tse2.mm.bing.net/th?id=OIP.def...&pid=15.1"
              }
            ]
          }
        }
        ```