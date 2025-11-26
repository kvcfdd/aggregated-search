# aggregated-search

```bash
git clone https://github.com/kvcfdd/aggregated-search.git
cd aggregated-search
pip install -r requirements.txt
uvicorn main:app
```

#### `GET /search`

-   **参数**:
    -   `q` (**必需**): 查询词。
    -   `type` (可选): `Information` 或 `image` (默认 `Information`)。
    -   `limit` (可选): 最终返回结果的条数 (默认 10, 范围 1–100)。

-   **请求示例**:

    *   **网页搜索**:
        ```bash
        curl -X GET "http://127.0.0.1:8000/search?type=Information&q=搜索关键词"
        ```

    *   **图片搜索**:
        ```bash
        curl -X GET "http://127.0.0.1:8000/search?type=image&q=搜索关键词"
        ```

-   **返回示例**:

    *   **网页搜索 - 摘要成功**:
        ```json
        {
          "code": 200,
          "message": "OK",
          "data": {
            "results": {
              "summary": "...",
              "sources": [
                {"id": 1, "title": "...", "url": "..."},
                {"id": 2, "title": "...", "url": "..."},
                {"id": 3, "title": "...", "url": "..."},
                {"id": 4, "title": "...", "url": "..."},
                {"id": 5, "title": "...", "url": "..."},
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
              {"title": "...", "description": "...", "url": "..."},
              {"title": "...", "description": "...", "url": "..."},
              {"title": "...", "description": "...", "url": "..."},
              {"title": "...", "description": "...", "url": "..."},
              {"title": "...", "description": "...", "url": "..."}
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
              {"title": "...", "source": "...", "url": "..."},
              {"title": "...", "source": "...", "url": "..."},
              {"title": "...", "source": "...", "url": "..."},
              {"title": "...", "source": "...", "url": "..."},
              {"title": "...", "source": "...", "url": "..."}
            ]
          }
        }
        ```