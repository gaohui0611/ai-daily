# GH AI早报

> AI 资讯早报，每日更新 AI 领域最新动态

## 使用方法

### 1. 创建 GitHub 仓库

```bash
# 在 GitHub 上创建新仓库 ai-daily
```

### 2. 配置 GitHub Pages

1. 进入仓库 Settings → Pages
2. Source 选择 `Deploy from a branch`
3. Branch 选择 `master` / `root`
4. 保存

### 3. 发布早报

在 Issues 中创建新的 Issue，标题格式建议：

```
2026-03-15 AI早报
```

内容使用 Markdown 格式，例如：

```markdown
## 今日要闻

### OpenAI 发布 GPT-5
OpenAI 今日宣布...

### Google Gemini 更新
Google 发布了...

## 开源项目推荐

### 项目1
描述...

## 工具推荐

### 工具1
描述...
```

### 4. 自动生成

创建 Issue 后，GitHub Actions 会自动：
- 生成 README.md
- 生成 RSS 订阅 (rss.xml)
- 备份 Issue 到 BACKUP 目录

## 订阅方式

- **RSS 订阅**: `https://gaohui0611.github.io/ai-daily/rss.xml`
- **GitHub Issues**: 直接在 Issues 中查看

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 本地运行（需要 GitHub Token）
python main.py YOUR_GITHUB_TOKEN gaohui0611/ai-daily
```

## 技术栈

- Python 3.11+
- PyGithub - GitHub API
- feedgen - RSS 生成
- marko - Markdown 解析

## Credits

基于 [gitblog](https://github.com/yihong0618/gitblog) 构建
