# -*- coding: utf-8 -*-
"""
AI 早报自动生成器 - 改进版
每日定时抓取 AI 资讯，生成早报内容并创建 Issue
改进内容：
- 添加醒目的原文链接按钮
- 添加文章分类标签
- 添加重要性评分
- 添加阅读时间估算
"""
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import feedparser
import requests
from bs4 import BeautifulSoup

# ============== 配置区域 ==============
# RSS 订阅源列表 (名称，RSS 链接，网站链接)
RSS_SOURCES = [
    # === AI 相关 ===
    ("OpenAI Blog", "https://openai.com/blog/rss.xml", "https://openai.com/blog"),
    ("Google AI Blog", "https://blog.google/technology/ai/rss/", "https://blog.google/technology/ai/"),
    ("Anthropic Blog", "https://www.anthropic.com/news/rss", "https://www.anthropic.com/news"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml", "https://huggingface.co/blog"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/", "https://www.technologyreview.com"),
    ("Microsoft AI Blog", "https://blogs.microsoft.com/ai/feed/", "https://blogs.microsoft.com/ai/"),
    ("DeepMind Blog", "https://deepmind.google/discover/blog/rss/", "https://deepmind.google/discover/blog/"),
    ("xAI Blog", "https://x.ai/blog/rss.xml", "https://x.ai/blog"),
    
    # === 程序员技术博客 ===
    ("阮一峰的网络日志", "https://www.ruanyifeng.com/blog/atom.xml", "https://www.ruanyifeng.com/blog/"),
    ("美团技术团队", "https://tech.meituan.com/feed/", "https://tech.meituan.com/"),
    ("字节跳动技术团队", "https://bytes.xtellar.net/feed.xml", "https://bytes.xtellar.net/"),
    ("酷壳 - 陈皓", "https://coolshell.cn/feed", "https://coolshell.cn/"),
    ("张鑫旭博客", "https://www.zhangxinxu.com/wordpress/feed/", "https://www.zhangxinxu.com/wordpress/"),
    ("廖雪峰博客", "https://www.liaoxuefeng.com/feed", "https://www.liaoxuefeng.com/"),
    
    # === 国际技术博客 ===
    ("GitHub Blog", "https://github.blog/feed/", "https://github.blog/"),
    ("Stack Overflow Blog", "https://stackoverflow.blog/feed/", "https://stackoverflow.blog/"),
    ("Netflix Tech Blog", "https://netflixtechblog.com/feed", "https://netflixtechblog.com/"),
    ("Uber Engineering", "https://www.uber.com/blog/engineering/rss/", "https://www.uber.com/blog/engineering/"),
    ("Twitter Engineering", "https://blog.twitter.com/engineering/en_us/blog.rss", "https://blog.twitter.com/engineering/"),
    ("Dropbox Tech Blog", "https://dropbox.tech/feed", "https://dropbox.tech/"),
    ("Cloudflare Blog", "https://blog.cloudflare.com/rss/", "https://blog.cloudflare.com/"),
    ("Vercel Blog", "https://vercel.com/feed", "https://vercel.com/blog"),
    
    # === 前端开发 ===
    ("React Blog", "https://react.dev/blog/rss.xml", "https://react.dev/blog"),
    ("Vue.js Blog", "https://blog.vuejs.org/feed.xml", "https://blog.vuejs.org/"),
    ("Node.js Blog", "https://nodejs.org/en/feed/blog.xml", "https://nodejs.org/en/blog/"),
    ("CSS-Tricks", "https://css-tricks.com/feed/", "https://css-tricks.com/"),
    ("Smashing Magazine", "https://www.smashingmagazine.com/feed/", "https://www.smashingmagazine.com/"),
    
    # === 后端/DevOps ===
    ("Docker Blog", "https://www.docker.com/feed/", "https://www.docker.com/blog/"),
    ("Kubernetes Blog", "https://kubernetes.io/feed.xml", "https://kubernetes.io/blog/"),
    ("AWS Blog", "https://aws.amazon.com/blogs/aws/feed/", "https://aws.amazon.com/blogs/aws/"),
    ("Google Cloud Blog", "https://cloud.google.com/feed/", "https://cloud.google.com/blog/"),
]

# Hacker News 关键词 (AI + 程序员相关)
HN_API = "https://hacker-news.firebaseio.com/v0"
HN_KEYWORDS = [
    # AI 相关
    "ai", "gpt", "llm", "openai", "anthropic", "claude", "gemini",
    "machine learning", "deep learning", "neural", "transformer",
    "chatbot", "artificial intelligence", "agi", "langchain",
    # 编程语言
    "python", "javascript", "typescript", "rust", "golang", "java",
    "react", "vue", "node.js", "deno", "bun",
    # 开发相关
    "programming", "developer", "software", "code", "api", "framework",
    "open source", "github", "git", "docker", "kubernetes", "devops",
    "database", "sql", "postgres", "redis", "linux", "terminal",
]

# GitHub Trending AI
GITHUB_TRENDING_URL = "https://github.com/trending?since=daily"

# 资讯数量限制
MAX_NEWS_PER_SOURCE = 3
MAX_TOTAL_NEWS = 12
MAX_PROJECTS = 5

# 分类关键词配置
CATEGORY_KEYWORDS = {
    "🤖 AI 模型": ["gpt", "llm", "claude", "gemini", "llama", "mistral", "transformer", "diffusion", "model"],
    "🚀 产品发布": ["release", "launch", "introduce", "announce", "new", "unveil"],
    "💻 开发工具": ["tool", "library", "framework", "sdk", "api", "vscode", "ide"],
    "📊 数据分析": ["data", "analytics", "visualization", "dashboard", "metric"],
    "🔒 安全隐私": ["security", "privacy", "vulnerability", "attack", "breach"],
    "☁️ 云服务": ["cloud", "aws", "azure", "gcp", "serverless", "saas"],
    "🎨 前端 UI": ["ui", "frontend", "css", "design", "component", "react", "vue"],
    "⚙️ 后端架构": ["backend", "architecture", "microservice", "database", "api"],
    "📱 移动开发": ["mobile", "ios", "android", "flutter", "react native"],
    "🔬 研究论文": ["research", "paper", "study", "experiment", "benchmark"],
}

# 重要性评分配置
PRIORITY_SOURCES = ["OpenAI", "Anthropic", "Google AI", "DeepMind", "MIT Technology Review"]
IMPORTANT_KEYWORDS = ["breakthrough", "major", "first", "revolutionary", "game-changing", "milestone"]


# =====================================


def clean_text(text: str) -> str:
    """清理文本，去除多余空白和 HTML 标签"""
    if not text:
        return ""
    # 去除 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_date(date_str: str) -> str:
    """解析日期字符串，返回 YYYY-MM-DD 格式"""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        # 尝试解析各种日期格式
        from dateutil import parser
        dt = parser.parse(date_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        # 如果解析失败，尝试直接截取
        return date_str[:10] if len(date_str) >= 10 else datetime.now().strftime("%Y-%m-%d")


def categorize_news(title: str, summary: str) -> List[str]:
    """
    根据标题和摘要为新闻分类
    
    Args:
        title: 新闻标题
        summary: 新闻摘要
    
    Returns:
        分类标签列表
    """
    tags = []
    text = f"{title} {summary}".lower()
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tags.append(category)
    
    # 如果没有匹配到分类，返回默认分类
    if not tags:
        tags.append("📰 综合资讯")
    
    return tags[:3]  # 最多返回 3 个分类


def calculate_importance(source: str, title: str, summary: str) -> Tuple[str, str]:
    """
    计算新闻的重要性评分
    
    Args:
        source: 来源名称
        title: 新闻标题
        summary: 新闻摘要
    
    Returns:
        (重要性图标，重要性描述) 元组
    """
    text = f"{title} {summary}".lower()
    source_lower = source.lower()
    
    # 检查是否来自权威来源
    is_priority_source = any(ps.lower() in source_lower for ps in PRIORITY_SOURCES)
    
    # 检查是否包含重要关键词
    has_important_keyword = any(kw in text for kw in IMPORTANT_KEYWORDS)
    
    # 检查是否是新品发布
    is_product_launch = any(kw in text for kw in ["release", "launch", "introduce", "new product"])
    
    # 检查是否是融资新闻
    is_funding = any(kw in text for kw in ["funding", "investment", "raised", "million", "billion"])
    
    # 计算重要性等级
    if is_priority_source and (has_important_keyword or is_product_launch):
        return ("🔥", "重要")
    elif is_product_launch or is_funding:
        return ("⭐", "新品")
    elif has_important_keyword:
        return ("✨", "热点")
    else:
        return ("📰", "资讯")


def estimate_reading_time(summary: str, title: str) -> str:
    """
    估算阅读时间
    
    Args:
        summary: 新闻摘要
        title: 新闻标题
    
    Returns:
        阅读时间字符串（如 "1 分钟"）
    """
    # 计算总字数（中英文混合）
    text = f"{title} {summary}"
    # 中文按字符数，英文按单词数估算
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    
    # 综合估算字数
    total_words = chinese_chars + english_words // 2
    
    # 假设阅读速度：300 字/分钟
    minutes = max(1, round(total_words / 300))
    
    if minutes <= 1:
        return "< 1 分钟"
    elif minutes <= 5:
        return f"{minutes} 分钟"
    else:
        return f"{minutes}+ 分钟"


def fetch_rss_news(source_name: str, feed_url: str, site_url: str) -> List[Dict]:
    """
    从 RSS 源抓取新闻
    
    Args:
        source_name: 来源名称
        feed_url: RSS 链接
        site_url: 网站链接
    
    Returns:
        新闻列表，包含标题、链接、来源、作者、时间、摘要、分类、重要性
    """
    news_list = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:MAX_NEWS_PER_SOURCE]:
            # 提取作者
            author = ""
            if hasattr(entry, 'author'):
                author = entry.author
            elif hasattr(entry, 'authors') and entry.authors:
                author = entry.authors[0].get('name', '')
            
            # 提取发布时间
            pub_date = ""
            if hasattr(entry, 'published'):
                pub_date = entry.published
            elif hasattr(entry, 'pubDate'):
                pub_date = entry.pubDate
            elif hasattr(entry, 'updated'):
                pub_date = entry.updated
            
            # 提取摘要
            summary = ""
            if hasattr(entry, 'summary'):
                summary = clean_text(entry.summary)[:300]
            elif hasattr(entry, 'description'):
                summary = clean_text(entry.description)[:300]
            
            title = entry.get("title", "")
            link = entry.get("link", "")
            
            # 添加分类和重要性评分
            categories = categorize_news(title, summary)
            importance_icon, importance_text = calculate_importance(source_name, title, summary)
            reading_time = estimate_reading_time(summary, title)
            
            news = {
                "title": title,
                "link": link,
                "original_url": link,  # 明确标识原文链接
                "source": source_name,
                "source_url": site_url,
                "author": author,
                "date": parse_date(pub_date),
                "summary": summary,
                "categories": categories,
                "importance_icon": importance_icon,
                "importance_text": importance_text,
                "reading_time": reading_time
            }
            if news["title"]:
                news_list.append(news)
    except Exception as e:
        print(f"❌ 抓取 {source_name} 失败：{e}")
    return news_list


def fetch_hn_ai_news() -> List[Dict]:
    """
    从 Hacker News 抓取 AI 相关热门新闻
    
    Returns:
        新闻列表
    """
    news_list = []
    try:
        # 获取 Top Stories
        response = requests.get(f"{HN_API}/topstories.json", timeout=10)
        story_ids = response.json()[:100]
        
        for story_id in story_ids[:50]:
            try:
                story_resp = requests.get(f"{HN_API}/item/{story_id}.json", timeout=10)
                story = story_resp.json()
                if not story:
                    continue
                
                title = story.get("title", "")
                title_lower = title.lower()
                url = story.get("url", "")
                
                # 检查是否包含关键词
                if any(kw in title_lower for kw in HN_KEYWORDS):
                    # 获取作者
                    author = story.get("by", "")
                    # 获取时间
                    timestamp = story.get("time", 0)
                    pub_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d") if timestamp else ""
                    
                    # 获取分数和评论数
                    score = story.get("score", 0)
                    descendants = story.get("descendants", 0)
                    
                    summary = f"HN 评分：{score} | 评论：{descendants}"
                    
                    # 添加分类和重要性
                    categories = categorize_news(title, summary)
                    importance_icon, importance_text = calculate_importance("Hacker News", title, summary)
                    reading_time = estimate_reading_time(summary, title)
                    
                    news = {
                        "title": title,
                        "link": url or f"https://news.ycombinator.com/item?id={story_id}",
                        "original_url": url or f"https://news.ycombinator.com/item?id={story_id}",
                        "source": "Hacker News",
                        "source_url": "https://news.ycombinator.com",
                        "author": author,
                        "date": pub_date,
                        "score": score,
                        "summary": summary,
                        "categories": categories,
                        "importance_icon": importance_icon,
                        "importance_text": importance_text,
                        "reading_time": reading_time
                    }
                    news_list.append(news)
                    
                    if len(news_list) >= MAX_NEWS_PER_SOURCE:
                        break
            except Exception:
                continue
        
        # 按分数排序
        news_list.sort(key=lambda x: x.get("score", 0), reverse=True)
    except Exception as e:
        print(f"❌ 抓取 Hacker News 失败：{e}")
    return news_list[:MAX_NEWS_PER_SOURCE]


def fetch_github_trending_ai() -> List[Dict]:
    """
    从 GitHub Trending 抓取 AI 相关热门项目
    
    Returns:
        项目列表
    """
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        response = requests.get(GITHUB_TRENDING_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        articles = soup.select("article.Box-row")[:20]
        for article in articles:
            try:
                repo_link = article.select_one("h2 a")
                if not repo_link:
                    continue
                
                repo_name = repo_link.get_text(strip=True).replace(" ", "")
                repo_url = f"https://github.com{repo_link.get('href', '')}"
                
                desc_elem = article.select_one("p.col-9")
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # 获取语言
                lang_elem = article.select_one("[itemprop='programmingLanguage']")
                language = lang_elem.get_text(strip=True) if lang_elem else ""
                
                # 获取 stars
                stars_elem = article.select_one("a[href$='/stargazers']")
                stars = stars_elem.get_text(strip=True) if stars_elem else "0"
                
                # 获取今日新增 stars
                today_stars_elem = article.select_one("span.float-sm-right")
                today_stars = today_stars_elem.get_text(strip=True) if today_stars_elem else ""
                
                # 检查是否 AI 相关
                desc_lower = description.lower()
                name_lower = repo_name.lower()
                ai_keywords = ["ai", "gpt", "llm", "chatbot", "machine-learning", "deep-learning",
                               "neural", "transformer", "openai", "claude", "gemini", "langchain",
                               "agent", "rag", "embedding", "vector", "llama", "mistral"]
                
                if any(kw in desc_lower or kw in name_lower for kw in ai_keywords):
                    projects.append({
                        "title": repo_name,
                        "link": repo_url,
                        "description": description,
                        "language": language,
                        "stars": stars,
                        "today_stars": today_stars,
                        "source": "GitHub Trending"
                    })
            except Exception:
                continue
                
    except Exception as e:
        print(f"❌ 抓取 GitHub Trending 失败：{e}")
    return projects[:MAX_PROJECTS]


def generate_daily_content() -> str:
    """
    生成每日早报内容
    
    Returns:
        Markdown 格式的早报内容
    """
    all_news = []
    all_projects = []
    
    # 抓取 RSS 新闻
    print("📡 开始抓取 RSS 源...")
    for name, rss_url, site_url in RSS_SOURCES:
        news = fetch_rss_news(name, rss_url, site_url)
        all_news.extend(news)
        print(f"  ✅ {name}: {len(news)} 条")
    
    # 抓取 Hacker News
    print("📡 抓取 Hacker News...")
    hn_news = fetch_hn_ai_news()
    all_news.extend(hn_news)
    print(f"  ✅ Hacker News: {len(hn_news)} 条")
    
    # 抓取 GitHub Trending
    print("📡 抓取 GitHub Trending...")
    gh_projects = fetch_github_trending_ai()
    all_projects.extend(gh_projects)
    print(f"  ✅ GitHub Trending: {len(gh_projects)} 个项目")
    
    # 去重并限制数量
    seen_titles = set()
    unique_news = []
    for news in all_news:
        title = news.get("title", "")
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_news.append(news)
    
    unique_news = unique_news[:MAX_TOTAL_NEWS]
    
    # 生成 Markdown 内容
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    content = f"""# {today} AI 早报
    
> 📅 {today} | 自动抓取自各大 AI 资讯源
> ⏰ 更新时间：{now}

---

## 📰 今日要闻

"""
    
    # 添加新闻（改进后的格式）
    if unique_news:
        for i, news in enumerate(unique_news, 1):
            title = news.get("title", "")
            link = news.get("link", "")
            original_url = news.get("original_url", link)
            source = news.get("source", "")
            author = news.get("author", "")
            date = news.get("date", "")
            summary = news.get("summary", "")
            categories = news.get("categories", [])
            importance_icon = news.get("importance_icon", "📰")
            importance_text = news.get("importance_text", "资讯")
            reading_time = news.get("reading_time", "1 分钟")
            
            # 生成分类标签字符串
            tags_str = " ".join(categories) if categories else "📰 综合资讯"
            
            content += f"### {i}. {importance_icon} {title}\n\n"
            content += f"| 属性 | 内容 |\n"
            content += f"| :--- | :--- |\n"
            content += f"| 📅 时间 | {date} |\n"
            content += f"| 🏷️ 分类 | {tags_str} |\n"
            content += f"| 📊 重要性 | {importance_icon} {importance_text} |\n"
            content += f"| ⏱️ 阅读 | {reading_time} |\n"
            if author:
                content += f"| 👤 作者 | {author} |\n"
            content += f"| 🔗 原文 | [**📖 查看原始文章 →**]({original_url}) |\n"
            content += f"\n"
            if summary:
                content += f"> 💬 {summary}\n\n"
            
            # 添加快速导航
            next_num = i + 1 if i < len(unique_news) else ""
            prev_num = i - 1 if i > 1 else ""
            nav_parts = []
            if prev_num:
                nav_parts.append(f"[← 上一条](#{prev_num})")
            if next_num:
                nav_parts.append(f"[下一条 →](#{next_num})")
            nav_parts.append("[↑ 返回顶部](#-今日要闻)")
            content += " | ".join(nav_parts)
            content += "\n\n"
            content += "---\n\n"
    else:
        content += "*今日暂无抓取到新闻*\n\n"
    
    # 添加 GitHub 项目
    if all_projects:
        content += "## 🔥 开源项目推荐\n\n"
        for i, project in enumerate(all_projects, 1):
            title = project.get("title", "")
            link = project.get("link", "")
            desc = project.get("description", "")
            language = project.get("language", "")
            stars = project.get("stars", "")
            today_stars = project.get("today_stars", "")
            
            content += f"### {i}. [{title}]({link})\n\n"
            content += f"| 属性 | 内容 |\n"
            content += f"| :--- | :--- |\n"
            if language:
                content += f"| 🔧 语言 | {language} |\n"
            if stars:
                content += f"| ⭐ Stars | {stars} |\n"
            if today_stars:
                content += f"| 📈 今日 | {today_stars} |\n"
            content += f"\n"
            if desc:
                content += f"> 📝 {desc}\n\n"
            content += "---\n\n"
    
    # 添加页脚
    content += f"""## 📬 订阅方式

| 方式 | 链接 |
| :--- | :--- |
| RSS 订阅 | [订阅](https://gaohui0611.github.io/ai-daily/rss.xml) |
| GitHub Issues | [查看](https://github.com/gaohui0611/ai-daily/issues) |
| Markdown 备份 | [BACKUP](https://github.com/gaohui0611/ai-daily/tree/master/BACKUP) |

---

## 📊 数据来源

### AI 资讯
| 来源 | 链接 |
| :--- | :--- |
| OpenAI Blog | [官网](https://openai.com/blog) |
| Google AI Blog | [官网](https://blog.google/technology/ai/) |
| Anthropic Blog | [官网](https://www.anthropic.com/news) |
| Hugging Face Blog | [官网](https://huggingface.co/blog) |
| MIT Technology Review | [官网](https://www.technologyreview.com) |
| Microsoft AI Blog | [官网](https://blogs.microsoft.com/ai/) |
| DeepMind Blog | [官网](https://deepmind.google/discover/blog/) |

### 技术博客
| 来源 | 链接 |
| :--- | :--- |
| 阮一峰的网络日志 | [官网](https://www.ruanyifeng.com/blog/) |
| 美团技术团队 | [官网](https://tech.meituan.com/) |
| 字节跳动技术团队 | [官网](https://bytes.xtellar.net/) |
| GitHub Blog | [官网](https://github.blog/) |
| Stack Overflow Blog | [官网](https://stackoverflow.blog/) |
| Netflix Tech Blog | [官网](https://netflixtechblog.com/) |

### 前端/框架
| 来源 | 链接 |
| :--- | :--- |
| React Blog | [官网](https://react.dev/blog) |
| Vue.js Blog | [官网](https://blog.vuejs.org/) |
| Node.js Blog | [官网](https://nodejs.org/en/blog/) |
| CSS-Tricks | [官网](https://css-tricks.com/) |

### DevOps/云服务
| 来源 | 链接 |
| :--- | :--- |
| Docker Blog | [官网](https://www.docker.com/blog/) |
| Kubernetes Blog | [官网](https://kubernetes.io/blog/) |
| AWS Blog | [官网](https://aws.amazon.com/blogs/aws/) |
| Cloudflare Blog | [官网](https://blog.cloudflare.com/) |

### 社区
| 来源 | 链接 |
| :--- | :--- |
| Hacker News | [官网](https://news.ycombinator.com) |
| GitHub Trending | [官网](https://github.com/trending) |

---

*本早报由脚本自动抓取生成，内容仅供参考。如需了解更多，请点击每条新闻的「查看原始文章」链接访问原文。*
"""
    
    return content


def create_daily_issue(token: str, repo_name: str, force: bool = False) -> Optional[int]:
    """
    创建每日早报 Issue
    
    Args:
        token: GitHub Token
        repo_name: 仓库名称
        force: 是否强制生成（即使今天已有）
    
    Returns:
        Issue 编号或 None
    """
    from github import Github
    
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"{today} AI 早报"
    
    # 检查是否已存在今天的 Issue
    g = Github(token)
    repo = g.get_repo(repo_name)
    
    existing_issue = None
    for issue in repo.get_issues(state="all"):
        if today in issue.title and "AI 早报" in issue.title:
            existing_issue = issue
            break
    
    if existing_issue and not force:
        print(f"⚠️ 今日早报已存在：{existing_issue.html_url}")
        print(f"💡 使用 force=true 强制生成新早报")
        return None
    
    # 如果强制生成且已存在，先关闭旧的
    if existing_issue and force:
        print(f"🔄 强制模式：关闭旧早报 #{existing_issue.number}")
        existing_issue.edit(state="closed")
    
    # 生成内容
    content = generate_daily_content()
    
    # 创建 Issue
    issue = repo.create_issue(title=title, body=content)
    print(f"✅ 创建成功：{issue.html_url}")
    
    return issue.number


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("GITHUB_REPOSITORY", "gaohui0611/ai-daily")
    force = os.environ.get("FORCE_GENERATE", "false").lower() == "true"
    
    if not token:
        print("❌ 请设置 GITHUB_TOKEN 环境变量")
        exit(1)
    
    print(f"🚀 开始生成早报 (force={force})")
    create_daily_issue(token, repo_name, force)
