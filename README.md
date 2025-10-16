# aggregated-search

一个简要的聚合搜索后端，供前端模型调用

## ✨ 功能特性

- **并发聚合搜索**: 同时从多个搜索引擎（当前仅有Bing, DuckDuckGo）抓取并整合搜索结果。
- **图像搜索**: SerpApi 图像搜索，支持 **API密钥池** 封号gg(单KEY免费额度250次/月，所以搜索才没用它dog)。
- **AI 摘要生成**: 使用 Google Gemini Pro 模型对搜索结果进行整合，生成高质量的中文摘要，默认2.0-flash，再高要被制裁了。

## 自跑

### 1. 先决条件

- Python 3.8+
- pip 包管理器

### 2. 安装步骤

1.  **克隆仓库**
    ```bash
    git clone https://github.xn--6rtu33f.top/kvcfdd/aggregated-search.git
    cd aggregated-search
    ```

2.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

3.  **创建配置文件**
    将 `.env.example` 文件复制一份并重命名为 `.env`。
    ```bash
    cp .env.example .env
    ```

4.  **编辑 `.env` 文件**
    打开 `.env` 文件，填入您的API密钥和可选的反代地址。详情请见下方的 **配置** 部分。

5.  **启动服务**
    ```bash
    uvicorn main:app --reload
    ```
    服务将在 `http://127.0.0.1:8000` 上运行。


## ⚙️ 配置

所有配置都在 `.env` 文件中完成。

| 变量 | 必需 | 描述 |
| :--- | :--- | :--- |
| `GOOGLE_API_KEY` | ❌ | 用于生成摘要的 Google Gemini API 密钥。可从 [Google AI Studio](https://aistudio.google.com/app/apikey) 获取。 |
| `SERPAPI_API_KEYS` | ✅ | 用于图像搜索的 SerpApi 密钥。可从 [SerpApi](https://serpapi.com/manage-api-key) 获取。 |
| `GEMINI_REVERSE_PROXY` | ❌ | Gemini API 的反向代理地址。国内服务器使用总结时必须配置。 |
| `DDG_REVERSE_PROXY` | ✅ | DuckDuckGo 搜索的反向代理地址，bing可能出现人机验证，这个再不配置就没得用了。 |
| `BING_REVERSE_PROXY` | ❌ | Bing 搜索的反向代理地址。实际上不要也行，该s还得s。 |


## 📡 API 使用文档

项目提供一个统一的 `GET /search` 接口。

**基础URL**: `http://127.0.0.1:8000`

### `GET /search`

#### 查询参数

| 参数 | 类型 | 必需 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- | :--- |
| `q` | string | ✅ | - | 搜索的关键词。 |
| `type` | string | ❌ | `text` | 搜索类型。可选值为 `text` 或 `image`。 |
| `limit` | integer | ❌ | `10` | 希望获取的结果数量。 |

---

### 示例 1: 文本搜索 (成功生成摘要)

**请求:**
```bash
curl -X GET "http://127.0.0.1:8000/search?type=text&q=人工智能的未来发展趋势"
```

**成功响应 (`200 OK`):**
```json
{
  "query": "人工智能的未来发展趋势",
  "status": "success",
  "content": "人工智能（AI）正以前所未有的速度发展，预计将深度融入社会各领域..."
}
```

---

### 示例 2: 文本搜索 (摘要失败)

**请求:**
```bash
curl -X GET "http://127.0.0.1:8000/search?type=text&q=一个非常罕见的查询"
```

**降级响应 (`200 OK`):**
```json
{
  "query": "一个非常罕见的查询",
  "status": "fallback",
  "content": "Source [1]:\nTitle: 相关标题1...\nSnippet: 相关摘要片段1...\nURL: http://example.com/page1\n\nSource [2]:\nTitle: 相关标题2...\nSnippet: 相关摘要片段2...\nURL: http://example.com/page2"
}
```

---

### 示例 3: 图像搜索

**请求:**
```bash
curl -X GET "http://127.0.0.1:8000/search?type=image&q=可爱的小猫&limit=2"
```

**成功响应 (`200 OK`):**
```json
{
  "query": "可爱的小猫",
  "images": [
    {
      "title": "可爱的小猫图片",
      "source": "example.com",
      "link": "https://example.com/page-with-cat-image",
      "original": "https://example.com/images/cute_cat_original.jpg",
      "thumbnail": "https://example.com/images/cute_cat_thumbnail.jpg"
    },
    {
      "title": "另一只可爱的小猫",
      "source": "another-site.net",
      "link": "https://another-site.net/gallery/cats",
      "original": "https://another-site.net/img/another_cat.png",
      "thumbnail": "https://another-site.net/img/another_cat_thumb.png"
    }
  ]
}
```

