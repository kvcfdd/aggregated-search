# aggregated-search

一个轻量级、可扩展的聚合搜索服务。

### 核心特性

- 多源聚合：异步调用多个搜索/图片源（示例子模块见 `search_providers/`）。
- 统一响应：对不同提供者的结果做规范化，返回一致的数据结构。
- 可扩展：通过在 `search_providers` 下添加新模块可以接入更多搜索引擎（通过test_single_provider进行测试）。

### 数据流

```text
HTTP 请求 (q, type)
│
▼
[ FastAPI Endpoint: /search ]
│
▼
[ 并发请求: Provider (DDG, Bing, Baidu...) ] ──> 聚合原始结果
│
▼
[ 智能处理管道 ]
│ 1. BM25 算法智能排序
│ 2. URL 规范化去重
│ 3. 内容相似度去重
│ 4. (可选) "enhance" 模式深度抓取
│
▼
[ 分支逻辑 ]
├─ (AI摘要成功) ──> [ Gemini API ] ──> 生成带引用的摘要
└─ (AI摘要失败) ──> 格式化排序后的结果列表
│
▼
[ HTTP 响应 ]
```

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
    uvicorn main:app
    ```

### API 概览

#### `GET /search`

-   **参数**:
    -   `q` (string, **必需**): 查询词。
    -   `type` (string, 可选): `'text'` 或 `'image'` (默认 `'text'`)。
    -   `limit` (int, 可选): 最终返回结果的条数 (默认 10, 范围 1–100)。
    -   `enhance` (string, 可选): 深入请求 `true` 或 `false` (默认 `false`)。

-   **请求示例**:

    *   **网页搜索**:
        ```bash
        curl -X GET "http://127.0.0.1:8000/search?type=text&q=搜索关键词"
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