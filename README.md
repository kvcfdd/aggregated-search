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

    *   **文本搜索 - 成功示例**:
        ```json
        {
          "code": 200,
          "message": "OK",
          "data": {
            "results": [
              {"title": "...", "url": "...", "description": "..."},
              {"title": "...", "url": "...", "description": "..."},
              {"title": "...", "url": "...", "description": "..."},
              {"title": "...", "url": "...", "description": "..."},
              {"title": "...", "url": "...", "description": "..."}
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
              {"title": "...", "url": "...", "source": "..."},
              {"title": "...", "url": "...", "source": "..."},
              {"title": "...", "url": "...", "source": "..."},
              {"title": "...", "url": "...", "source": "..."},
              {"title": "...", "url": "...", "source": "..."}
            ]
          }
        }
        ```