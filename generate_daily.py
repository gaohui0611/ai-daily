# -*- coding: utf-8 -*-
"""
AI早报自动生成器
每日定时抓取 AI 资讯，生成早报内容并创建 Issue
"""
import os
import re
from datetime import datetime
from typing import List, Dict, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

# ============== 配置区域 ==============
# RSS 订阅源列表 (名称, RSS链接, 网站链接)
RSS_SOURCES = [
    ("OpenAI Blog", "https://openai.com/blog/rss.xml", "https://openai.com/blog"),
    ("Google AI Blog", "https://blog.google/technology/ai/rss/", "https://blog.google/technology/ai/"),
    ("Anthropic Blog", "https://www.anthropic.com/news/rss", "https://www.anthropic.com/news"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml", "https://huggingface.co/blog"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/", "https://www.technologyreview.com"),
    ("Microsoft AI Blog", "https://blogs.microsoft.com/ai/feed/", "https://blogs.microsoft.com/ai/"),
    ("DeepMind Blog", "https://deepmind.google/discover/blog/rss/", "https://deepmind.google/discover/blog/"),
]

# Hacker News AI 相关
HN_API = "https://hacker-news.firebaseio.com/v0"
HN_AI_KEYWORDS = ["ai", "gpt", "llm", "openai", "anthropic", "claude", "gemini",
                  "machine learning", "deep learning", "neural", "transformer",
                  "chatbot", "artificial intelligence", "agi", "langchain"]

# GitHub Trending AI
GITHUB_TRENDING_URL = "https://github.com/trending?since=daily"

# 资讯数量限制
MAX_NEWS_PER_SOURCE = 3
MAX_TOTAL_NEWS = 12
MAX_PROJECTS = 5
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


def fetch_rss_news(source_name: str, feed_url: str, site_url: str) -> List[Dict]:
    """
    从 RSS 源抓取新闻

    Args:
        source_name: 来源名称
        feed_url: RSS 链接
        site_url: 网站链接

    Returns:
        新闻列表，包含标题、链接、来源、作者、时间、摘要
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

            news = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "source": source_name,
                "source_url": site_url,
                "author": author,
                "date": parse_date(pub_date),
                "summary": summary
            }
            if news["title"]:
                news_list.append(news)
    except Exception as e:
        print(f"❌ 抓取 {source_name} 失败: {e}")
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

                title = story.get("title", "").lower()
                url = story.get("url", "")

                # 检查是否包含 AI 关键词
                if any(kw in title for kw in HN_AI_KEYWORDS):
                    # 获取作者
                    author = story.get("by", "")
                    # 获取时间
                    timestamp = story.get("time", 0)
                    pub_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d") if timestamp else ""

                    news = {
                        "title": story.get("title", ""),
                        "link": url or f"https://news.ycombinator.com/item?id={story_id}",
                        "source": "Hacker News",
                        "source_url": "https://news.ycombinator.com",
                        "author": author,
                        "date": pub_date,
                        "score": story.get("score", 0),
                        "summary": f"HN 评分: {story.get('score', 0)} | 评论: {story.get('descendants', 0)}"
                    }
                    news_list.append(news)

                    if len(news_list) >= MAX_NEWS_PER_SOURCE:
                        break
            except Exception:
                continue

        # 按分数排序
        news_list.sort(key=lambda x: x.get("score", 0), reverse=True)
    except Exception as e:
        print(f"❌ 抓取 Hacker News 失败: {e}")
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
                today_stars = ""
                if today_stars_elem:
                    today_stars = today_stars_elem.get_text(strip=True)

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
        print(f"❌ 抓取 GitHub Trending 失败: {e}")
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

    content = f"""# {today} AI早报

> 📅 {today} | 自动抓取自各大 AI 资讯源
> ⏰ 更新时间: {now}

---

## 📰 今日要闻

"""

    # 添加新闻
    if unique_news:
        for i, news in enumerate(unique_news, 1):
            title = news.get("title", "")
            link = news.get("link", "")
            source = news.get("source", "")
            source_url = news.get("source_url", "")
            author = news.get("author", "")
            date = news.get("date", "")
            summary = news.get("summary", "")

            content += f"### {i}. [{title}]({link})\n\n"
            content += f"| 属性 | 内容 |\n"
            content += f"| :--- | :--- |\n"
            content += f"| 📅 时间 | {date} |\n"
            content += f"| 🏷️ 来源 | [{source}]({source_url}) |\n"
            if author:
                content += f"| 👤 作者 | {author} |\n"
            content += f"\n"
            if summary:
                content += f"> 💬 {summary}\n\n"
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

| 来源 | 链接 |
| :--- | :--- |
| OpenAI Blog | [官网](https://openai.com/blog) |
| Google AI Blog | [官网](https://blog.google/technology/ai/) |
| Anthropic Blog | [官网](https://www.anthropic.com/news) |
| Hugging Face Blog | [官网](https://huggingface.co/blog) |
| MIT Technology Review | [官网](https://www.technologyreview.com) |
| Hacker News | [官网](https://news.ycombinator.com) |
| GitHub Trending | [官网](https://github.com/trending) |

---

*本早报由脚本自动抓取生成，内容仅供参考。如需了解更多，请访问原始链接。*
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
    title = f"{today} AI早报"

    # 检查是否已存在今天的 Issue
    g = Github(token)
    repo = g.get_repo(repo_name)

    existing_issue = None
    for issue in repo.get_issues(state="all"):
        if today in issue.title and "AI早报" in issue.title:
            existing_issue = issue
            break

    if existing_issue and not force:
        print(f"⚠️ 今日早报已存在: {existing_issue.html_url}")
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
    print(f"✅ 创建成功: {issue.html_url}")

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
