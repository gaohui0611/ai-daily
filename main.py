# -*- coding: utf-8 -*-
"""
AI早报生成器
基于 gitblog 项目，将 GitHub Issues 转换为 Markdown 和 RSS 订阅
"""
import argparse
import html
import os
import re

import markdown
from feedgen.ext.base import BaseExtension
from feedgen.feed import FeedGenerator
from github import Github
from lxml import html as lxml_html
from lxml import etree as lxml_etree
from lxml.etree import tostring
from marko.ext.gfm import gfm as marko

# ============== 配置区域 ==============
SITE_TITLE = "GH AI早报"
SITE_DESCRIPTION = "AI 资讯早报，每日更新 AI 领域最新动态"
AUTHOR_NAME = "GH"
AUTHOR_EMAIL = "gh@example.com"
FEED_FILENAME = "rss.xml"
FEED_ICON_PATH = "static/icon.svg"
FEED_ICON_SIZE = 144
RSS_SUMMARY_MAX_CHARS = 360
WEBFEEDS_NS = "http://webfeeds.org/rss/1.0"
BACKUP_DIR = "BACKUP"
ANCHOR_NUMBER = 10  # 首页显示的文章数
# =====================================

MD_HEAD = """# {site_title}

> AI 资讯早报，每日更新 AI 领域最新动态。资讯内容由 AI 辅助生成，可能存在错误，请以原始信息出处和官方信息为准。

## 订阅方式

| 方式 | 链接 |
| :--- | :--- |
| RSS 订阅 | [订阅]({feed_subscribe_url}) |
| Markdown 备份 | [BACKUP](https://github.com/{repo_name}/tree/{branch_name}/BACKUP) |
| GitHub Pages | [查看](https://{owner}.github.io/{repo}/) |

---

"""


def get_me(user):
    return user.get_user().login


def get_me_from_repo(repo):
    return repo.owner.login


def is_me(issue, me):
    return issue.user.login == me


def format_time(time):
    return str(time)[:10]


def get_pages_base_url(repo_name):
    owner, repo = repo_name.split("/", 1)
    return f"https://{owner}.github.io/{repo}"


def get_pages_feed_url(repo_name, feed_filename):
    return f"{get_pages_base_url(repo_name)}/{feed_filename}"


def get_repo_pages_issue_url(repo, issue_number):
    return f"https://{repo.owner.login}.github.io/{repo.name}/issue-{issue_number}/"


def login(token):
    return Github(token)


def get_repo(user: Github, repo: str):
    return user.get_repo(repo)


def _valid_xml_char_ordinal(c):
    codepoint = ord(c)
    return (
        0x20 <= codepoint <= 0xD7FF
        or codepoint in (0x9, 0xA, 0xD)
        or 0xE000 <= codepoint <= 0xFFFD
        or 0x10000 <= codepoint <= 0x10FFFF
    )


def add_issue_info(issue, md):
    time = format_time(issue.created_at)
    md.write(f"- [{issue.title}]({issue.html_url})--{time}\n")


def add_md_recent(repo, md, me, limit=ANCHOR_NUMBER):
    count = 0
    with open(md, "a+", encoding="utf-8") as md_file:
        md_file.write("## 最近更新\n\n")
        try:
            for issue in repo.get_issues(state="all", sort="created", direction="desc"):
                if issue.pull_request:
                    continue
                if is_me(issue, me):
                    add_issue_info(issue, md_file)
                    count += 1
                    if count >= limit:
                        break
        except Exception as e:
            print(str(e))


def add_md_header(md, repo_name, feed_filename, branch_name, site_title):
    owner = repo_name.split("/")[0]
    repo = repo_name.split("/")[1] if "/" in repo_name else repo_name
    with open(md, "w", encoding="utf-8") as md_file:
        md_file.write(
            MD_HEAD.format(
                site_title=site_title,
                repo_name=repo_name,
                branch_name=branch_name,
                feed_subscribe_url=get_pages_feed_url(repo_name, feed_filename),
                owner=owner,
                repo=repo,
            )
        )
        md_file.write("\n")


def add_md_all_issues(repo, md, me):
    """添加所有 Issues 分类显示"""
    with open(md, "a+", encoding="utf-8") as md_file:
        md_file.write("## 全部早报\n\n")
        md_file.write("<details><summary>点击展开全部</summary>\n\n")

        try:
            for issue in repo.get_issues(state="all", sort="created", direction="desc"):
                if issue.pull_request:
                    continue
                if is_me(issue, me):
                    add_issue_info(issue, md_file)
        except Exception as e:
            print(str(e))

        md_file.write("</details>\n\n")


def add_md_footer(md):
    footer = """
---

## 关于

本早报基于 [gitblog](https://github.com/yihong0618/gitblog) 构建。

## License

- 代码：[MIT](./LICENSE)
- 文章内容：[CC BY-NC 4.0](./LICENSE-CONTENT)
"""
    with open(md, "a+", encoding="utf-8") as md_file:
        md_file.write(footer)


def get_to_generate_issues(repo, dir_name, me, issue_number=None):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    md_files = os.listdir(dir_name) if os.path.exists(dir_name) else []
    generated_issues_numbers = [
        int(i.split("_")[0]) for i in md_files if i.split("_")[0].isdigit()
    ]
    to_generate_issues = [
        i
        for i in list(repo.get_issues(state="all", sort="created", direction="desc"))
        if int(i.number) not in generated_issues_numbers
        and i.body
        and is_me(i, me)
        and not i.pull_request
    ]
    if issue_number:
        issue = repo.get_issue(int(issue_number))
        issue_numbers = {i.number for i in to_generate_issues}
        if issue.number not in issue_numbers and issue.body and is_me(issue, me) and not issue.pull_request:
            to_generate_issues.append(issue)
    return to_generate_issues


def normalize_rss_html(content):
    try:
        fragments = lxml_html.fragments_fromstring(content)
        normalized = []
        for fragment in fragments:
            if isinstance(fragment, str):
                normalized.append(fragment)
            else:
                normalized.append(tostring(fragment, encoding="unicode", method="html"))
        return "".join(normalized)
    except Exception:
        return content


def html_to_plain_text(content):
    try:
        fragment = lxml_html.fragment_fromstring(content, create_parent="div")
        text = fragment.text_content()
    except Exception:
        text = re.sub(r"<[^>]+>", " ", content)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def make_rss_summary(content, max_chars=RSS_SUMMARY_MAX_CHARS):
    summary = html_to_plain_text(content)
    if len(summary) <= max_chars:
        return summary
    return summary[: max_chars - 1].rstrip() + "…"


class WebfeedsExtension(BaseExtension):
    def __init__(self):
        self._icon = None
        self._logo = None

    def extend_ns(self):
        return {"webfeeds": WEBFEEDS_NS}

    def extend_rss(self, rss_feed):
        channel = rss_feed[0]
        if self._icon:
            icon = lxml_etree.SubElement(channel, f"{{{WEBFEEDS_NS}}}icon")
            icon.text = self._icon
        if self._logo:
            logo = lxml_etree.SubElement(channel, f"{{{WEBFEEDS_NS}}}logo")
            logo.text = self._logo
        return rss_feed

    def icon(self, value=None):
        if value is not None:
            self._icon = value
        return self._icon

    def logo(self, value=None):
        if value is not None:
            self._logo = value
        return self._logo


def generate_rss_feed(repo, filename, me, site_title, site_description, author_name, author_email):
    pages_site_url = f"{get_pages_base_url(repo.full_name)}/"
    feed_self_url = get_pages_feed_url(repo.full_name, filename)
    generator = FeedGenerator()
    generator.id(repo.html_url)
    generator.title(site_title)
    generator.description(site_description)
    generator.language("zh-CN")
    generator.author({"name": author_name, "email": author_email})
    generator.link(href=feed_self_url, rel="self", type="application/rss+xml")
    generator.link(href=pages_site_url)

    feed_icon_url = f"{pages_site_url}icon.svg"
    if os.path.exists(FEED_ICON_PATH):
        generator.load_extension("podcast")
        generator.podcast.itunes_image(feed_icon_url)
        generator.register_extension(
            "webfeeds",
            extension_class_feed=WebfeedsExtension,
            atom=False,
            rss=True,
        )
        generator.webfeeds.icon(feed_icon_url)
        generator.webfeeds.logo(feed_icon_url)
        generator.image(
            url=feed_icon_url,
            title=site_title,
            link=pages_site_url,
            width=str(FEED_ICON_SIZE),
            height=str(FEED_ICON_SIZE),
            description=f"{site_title} RSS 图标",
        )

    for issue in repo.get_issues(state="all", sort="created", direction="desc"):
        if not issue.body or not is_me(issue, me) or issue.pull_request:
            continue
        issue_pages_url = get_repo_pages_issue_url(repo, issue.number)
        item = generator.add_entry(order="append")
        item.id(issue.html_url)
        item.link(href=issue_pages_url)
        item.title(issue.title)
        item.author({"name": author_name})
        item.published(issue.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"))
        for label in issue.labels:
            item.category({"term": label.name})
        body = "".join(c for c in issue.body if _valid_xml_char_ordinal(c))
        full_content = normalize_rss_html(marko.convert(body))
        summary = make_rss_summary(full_content) or issue.title
        item.description(summary)
        item.content(full_content, type="CDATA")

    generator.rss_file(filename)


def save_issue(issue, me, dir_name=BACKUP_DIR):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    md_name = os.path.join(
        dir_name, f"{issue.number}_{issue.title.replace('/', '-').replace(' ', '.')}.md"
    )
    with open(md_name, "w", encoding="utf-8") as f:
        f.write(f"# [{issue.title}]({issue.html_url})\n\n")
        f.write(issue.body or "")
        if issue.comments:
            for c in issue.get_comments():
                if is_me(c, me):
                    f.write("\n\n---\n\n")
                    f.write(c.body or "")


def main(token, repo_name, issue_number=None, dir_name=BACKUP_DIR):
    user = login(token)
    repo = get_repo(user, repo_name)
    me = get_me_from_repo(repo)
    default_branch = repo.default_branch or "master"

    # 生成 README.md
    add_md_header("README.md", repo_name, FEED_FILENAME, default_branch, SITE_TITLE)
    add_md_recent(repo, "README.md", me)
    add_md_all_issues(repo, "README.md", me)
    add_md_footer("README.md")

    # 生成 RSS
    generate_rss_feed(repo, FEED_FILENAME, me, SITE_TITLE, SITE_DESCRIPTION, AUTHOR_NAME, AUTHOR_EMAIL)

    # 备份 Issues
    to_generate_issues = get_to_generate_issues(repo, dir_name, me, issue_number)
    for issue in to_generate_issues:
        save_issue(issue, me, dir_name)

    print(f"✅ 生成完成! 处理了 {len(to_generate_issues)} 个新 Issues")


if __name__ == "__main__":
    if not os.path.exists(BACKUP_DIR):
        os.mkdir(BACKUP_DIR)
    parser = argparse.ArgumentParser(description="AI早报生成器")
    parser.add_argument("github_token", help="GitHub Token")
    parser.add_argument("repo_name", help="仓库名称 (格式: owner/repo)")
    parser.add_argument("--issue_number", help="指定 Issue 编号", default=None, required=False)
    options = parser.parse_args()
    main(options.github_token, options.repo_name, options.issue_number)
