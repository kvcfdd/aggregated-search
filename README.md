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
    所有配置都在 `.env` 文件中完成。
    ```bash
    cp .env.example .env
    ```

5.  **启动服务**
    ```bash
    uvicorn main:app --reload
    ```
    服务将在 `http://127.0.0.1:8000` 上运行。


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
curl -X GET "http://127.0.0.1:8000/search?type=text&q=今汐"
```

**成功响应 (`200 OK`):**
```json
{
  "query": "今汐",
  "status": "success",
  "content": "今汐，原名汐，是游戏《鸣潮》中的角色，今州令尹，出生于今州云霄山。16年前，她在云霄山残象潮中夭折，后被岁主“角”复活，成为“角”的共鸣者，并被“角”带到今州抚养长大。幼时拜长离为师，学习武艺和技艺，并在长离的辅佐下，于豆蔻之年被岁主“角”任命为今州令尹，仅用3年就带领今州走出弯刀之役，重获繁荣。\n\n今汐是对玩家角色漂泊者表现出好感的角色之一，其师父长离也同样对漂泊者表现出较多好感，因此衍生出“师傅你不要抢我老公啊”的梗，并伴随有许多颠覆形象的表情包与二创。韩国画师Are_A_R画了一副今汐在雪地中泪流满面追逐漂泊者的图。由于后续推出的角色如“长离”、“守岸人”等与漂泊者的亲密度、恋爱感，今汐在玩家社群内被贴上败犬标签。\n\n今汐的共鸣回路的Pt，可以通过团队成员（包括今汐自身）的攻击命中敌人，同属性攻击每3秒获得1次。关于今汐的技能机制、专武推荐、声骸选择、合轴打法等方面的心得，可以参考相关攻略。\n\n如果玩家在抽取今汐的命座和专属武器之间犹豫，建议优先抽取专属武器，其次是1~2命。专属武器对今汐来说是最强的武器，如果还有余力，可以考虑抽取2命，2命效果为非战斗时能量会自动充满。\n\n今汐背负着今州代表的重任，并衷心希望人们拥有美好的未来。"
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

