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
# RSS 订阅源列表
RSS_SOURCES = [
    ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
    ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    ("Anthropic Blog", "https://www.anthropic.com/news/rss"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
    ("MIT AI News", "https://www.technologyreview.com/feed/"),
]

# Hacker News AI 相关
HN_API = "https://hacker-news.firebaseio.com/v0"
HN_AI_KEYWORDS = ["ai", "gpt", "llm", "openai", "anthropic", "claude", "gemini", "machine learning", "deep learning"]

# GitHub Trending AI
GITHUB_TRENDING_URL = "https://github.com/trending?since=daily"

# 资讯数量限制
MAX_NEWS_PER_SOURCE = 3
MAX_TOTAL_NEWS = 10
# =====================================


def fetch_rss_news(source_name: str, feed_url: str) -> List[Dict]:
    """
    从 RSS 源抓取新闻

    Args:
        source_name: 来源名称
        feed_url: RSS 链接

    Returns:
        新闻列表
    """
    news_list = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:MAX_NEWS_PER_SOURCE]:
            news = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "source": source_name,
                "summary": entry.get("summary", "")[:200] if entry.get("summary") else "",
                "date": entry.get("published", "")[:10] if entry.get("published") else ""
            }
            if news["title"]:
                news_list.append(news)
    except Exception as e:
        print(f"抓取 {source_name} 失败: {e}")
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
                    news = {
                        "title": story.get("title", ""),
                        "link": url or f"https://news.ycombinator.com/item?id={story_id}",
                        "source": "Hacker News",
                        "score": story.get("score", 0),
                        "date": datetime.fromtimestamp(story.get("time", 0)).strftime("%Y-%m-%d")
                    }
                    news_list.append(news)

                    if len(news_list) >= MAX_NEWS_PER_SOURCE:
                        break
            except Exception:
                continue

        # 按分数排序
        news_list.sort(key=lambda x: x.get("score", 0), reverse=True)
    except Exception as e:
        print(f"抓取 Hacker News 失败: {e}")
    return news_list[:MAX_NEWS_PER_SOURCE]


def fetch_github_trending_ai() -> List[Dict]:
    """
    从 GitHub Trending 抓取 AI 相关热门项目

    Returns:
        项目列表
    """
    projects = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(GITHUB_TRENDING_URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.select("article.Box-row")[:10]
        for article in articles:
            try:
                repo_link = article.select_one("h2 a")
                if not repo_link:
                    continue

                repo_name = repo_link.get_text(strip=True).replace(" ", "")
                repo_url = f"https://github.com{repo_link.get('href', '')}"

                desc_elem = article.select_one("p.col-9")
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                # 检查是否 AI 相关
                desc_lower = description.lower()
                name_lower = repo_name.lower()
                ai_keywords = ["ai", "gpt", "llm", "chatbot", "machine-learning", "deep-learning",
                               "neural", "transformer", "openai", "claude", "gemini", "langchain"]

                if any(kw in desc_lower or kw in name_lower for kw in ai_keywords):
                    projects.append({
                        "title": repo_name,
                        "link": repo_url,
                        "description": description,
                        "source": "GitHub Trending"
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"抓取 GitHub Trending 失败: {e}")
    return projects[:5]


def generate_daily_content() -> str:
    """
    生成每日早报内容

    Returns:
        Markdown 格式的早报内容
    """
    all_news = []
    all_projects = []

    # 抓取 RSS 新闻
    for name, url in RSS_SOURCES:
        news = fetch_rss_news(name, url)
        all_news.extend(news)
        print(f"✅ {name}: {len(news)} 条新闻")

    # 抓取 Hacker News
    hn_news = fetch_hn_ai_news()
    all_news.extend(hn_news)
    print(f"✅ Hacker News: {len(hn_news)} 条新闻")

    # 抓取 GitHub Trending
    gh_projects = fetch_github_trending_ai()
    all_projects.extend(gh_projects)
    print(f"✅ GitHub Trending: {len(gh_projects)} 个项目")

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
    content = f"""## 今日要闻

> 📅 {today} | 自动抓取自各大 AI 资讯源

"""

    # 添加新闻
    if unique_news:
        for i, news in enumerate(unique_news, 1):
            title = news.get("title", "")
            link = news.get("link", "")
            source = news.get("source", "")
            content += f"### {i}. [{title}]({link})\n"
            content += f"> 来源: {source}\n\n"
    else:
        content += "*今日暂无抓取到新闻*\n\n"

    # 添加 GitHub 项目
    if all_projects:
        content += "## 开源项目推荐\n\n"
        for i, project in enumerate(all_projects, 1):
            title = project.get("title", "")
            link = project.get("link", "")
            desc = project.get("description", "")
            content += f"### {i}. [{title}]({link})\n"
            if desc:
                content += f"{desc}\n\n"

    # 添加页脚
    content += """---

## 订阅方式

- RSS: [订阅早报](https://gaohui0611.github.io/ai-daily/rss.xml)
- GitHub: [查看源码](https://github.com/gaohui0611/ai-daily)

---
*本早报由脚本自动抓取生成，内容仅供参考*
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
