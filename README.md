# aggregated-search API

一个轻量级的聚合搜索API。

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

### API 概览

#### `GET /search`

-   **参数**:
    -   `q` (string, **必需**): 查询词。
    -   `type` (string, 可选): `'text'` 或 `'image'` (默认 `'text'`)。
    -   `limit` (int, 可选): 最终返回结果的条数 (默认 10, 范围 1–100)。
    -   `enhance` (string, 可选): 深入请求 `'true'` 或 `'false'` (默认 `'false'`)。

    **enhance** 参数会有额外轻微延迟

-   **请求示例**:

    *   **文本搜索**:
        ```bash
        curl -X GET "http://127.0.0.1:8000/search?type=text&q=FastAPI最佳实践"
        ```

    *   **图片搜索**:
        ```bash
        curl -X GET "http://127.0.0.1:8000/search?type=image&q=风景壁纸"
        ```

-   **返回示例**:

    *   **文本搜索 - 摘要成功**:
        ```json
        {
          "code": 200,
          "message": "OK",
          "data": {
            "results": {
              "summary": "FastAPI 是一个现代、高性能的 Python Web 框架，基于 Starlette 和 Pydantic 构建 [1, 2]。它的核心优势在于通过类型提示实现的高性能和自动生成的交互式API文档 [3]。",
              "sources": [
                {
                  "id": 1,
                  "title": "FastAPI Best Practices - Real Python",
                  "url": "https://realpython.com/fastapi-best-practices/"
                },
                {
                  "id": 2,
                  "title": "A Comprehensive Guide to FastAPI Best Practices - ...",
                  "url": "https://example.com/fastapi-guide"
                },
                {
                  "id": 3,
                  "title": "FastAPI 官网文档 - Tiangolo",
                  "url": "https://fastapi.tiangolo.com/"
                },
              ]
            }
          }
        }
        ```

    *   **文本搜索 - 回退列表**:
        ```json
        {
          "code": 200,
          "message": "OK",
          "data": {
            "results": [
              {
                "title": "FastAPI Best Practices - Real Python",
                "description": "Learn about the best practices for building robust and maintainable APIs with FastAPI...",
                "url": "https://realpython.com/fastapi-best-practices/"
              },
              {
                "title": "A Comprehensive Guide to FastAPI Best Practices - ...",
                "description": "Explore dependency injection, testing, project structure, and more to build production-ready FastAPI applications.",
                "url": "https://example.com/fastapi-guide"
              }
            ]
          }
        }
        ```

    *   **图片搜索 - 成功示例**:
        ```json
        {
          "code": 200,
          "message": "OK",
          "data": {
            "images": [
              {
                "title": "4K高清唯美风景壁纸 - Pexels",
                "source": "pexels.com",
                "url": "https://images.pexels.com/photos/12345/landscape.jpeg"
              },
              {
                "title": "瑞士山脉湖泊风景桌面壁纸",
                "source": "wallpaperhub.app",
                "url": "https://wallpaperhub.app/images/swiss-mountains.jpg"
              }
            ]
          }
        }
        ```