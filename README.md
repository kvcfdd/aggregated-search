# aggregated-search API

一个轻量级的聚合搜索服务。

### 快速开始

1.  克隆项目并安装依赖：

    ```bash
    git clone https://github.com/your-repo/aggregated-search.git
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

- **参数**:
    - `q` (string, **必需**): 查询词。
    - `type` (string, 可选): `'text'` 或 `'image'` (默认 `'text'`)。
    - `limit` (int, 可选): 最终返回结果的条数 (默认 10, 范围 1–30)。


- **请求示例**

```bash
curl -X GET "http://127.0.0.1:8000/search?type=text&q=FastAPI最佳实践"
```

- **返回示例**:

**摘要成功示例 (`message: "OK"`)**:

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

- **回退示例 (message: "fallback")**:

```json
{
  "success": true,
  "code": 200,
  "message": "fallback",
  "data": {
    "query": "FastAPI 最佳实践",
    "results": [
      {
        "source": 1,
        "title": "FastAPI Best Practices - Real Python",
        "description": "Learn about the best practices for building robust and maintainable APIs with FastAPI...",
        "url": "https://realpython.com/fastapi-best-practices/"
      }
    ]
  }
}
```
