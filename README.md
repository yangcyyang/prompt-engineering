# prompt-engineering

适用于 OpenClaw / Claude Code 的提示词工程 Skill。

说出你的需求，它自动从本地知识库检索相似提示词；没有匹配时，按 [LangGPT](https://github.com/langgptai/LangGPT) 格式生成一份结构化提示词。

---

## 核心能力

| 能力 | 说明 |
|------|------|
| **KB 检索** | SQLite FTS5 全文索引，中文逐字切分，返回 Top-3 相关结果 |
| **LangGPT 生成** | 无匹配时自动生成，无需用户二次确认 |
| **意图路由** | 自动判断「搜库」还是「直接生成」，模糊时只问一个问题 |
| **原子化提取** | 自动从 Markdown 知识库中拆分子提示词，导出为独立 `.md` 文件 |
| **零外部依赖** | 仅依赖 Python 标准库 |

---

## 目录结构

```
prompt-engineering/
├── SKILL.md                    # Skill 入口（意图路由表 + Actions 定义）
├── engine.py                   # CLI 入口：检索 / LangGPT 生成
├── indexer.py                  # 知识库提取 + SQLite FTS5 索引构建
├── retriever.py                # FTS5 查询封装
├── run.py                      # 交互式入口（Skill 调用的主脚本）
├── templates/
│   └── langgpt_default.md      # LangGPT 提示词模板
└── prompts/                    # 自动导出的原子提示词（可直接阅读）
    ├── AI营销_解压/
    └── 姚金刚提示词合集/
```

---

## 快速开始

### 在 OpenClaw / Claude Code 中使用

将本目录放入你的 skills 路径：

```bash
# OpenClaw
cp -r prompt-engineering ~/.openclaw/workspace/skills/

# Claude Code
cp -r prompt-engineering ~/.claude/skills/
```

然后直接对话：

> 「帮我找一个 GEO 营销的提示词」  
> 「生成一个小红书文案助手的系统提示」  
> 「有没有客服相关的 prompt 模板」

### 命令行直接使用

```bash
# 检索知识库
python3 engine.py "客服助手"

# 知识库无匹配时自动生成 LangGPT 提示词
python3 engine.py "量子计算科普专家"

# 选择并查看完整提示词
python3 run.py select_prompt 1
```

---

## 接入自己的知识库

修改 `indexer.py` 顶部的 `DEFAULT_KB_PATHS`，指向你本地的 Markdown 文件：

```python
DEFAULT_KB_PATHS = [
    "/path/to/your/prompts.md",
    "/path/to/another/collection.md",
]
```

然后重建索引：

```bash
python3 indexer.py
```

索引完成后自动导出所有原子提示词到 `prompts/` 目录。

---

## 使用示例

### 搜库有结果

```
> 帮我找一个营销文案的提示词

🔍 找到 3 个相关提示词：

1. **AI友好内容创作提示词**（来源：AI营销_解压.md）
   你是一位内容创作专家，擅长...

2. **内容工程化生产提示词**（来源：AI营销_解压.md）
   ...

3. **SEO到GEO转型对比分析提示词**（来源：AI营销_解压.md）
   ...

💡 请回复数字 1、2 或 3 选择你想要的提示词，或回复 0 取消。
```

### 搜库无结果时自动生成

```
> 生成一个区块链技术顾问的提示词

📭 知识库中暂无匹配。已为你按 LangGPT 格式生成：

# Role: 区块链技术顾问

## Profile
- Description: 你是一位专业的区块链技术顾问，专注于帮助用户...
...
```

### 意图模糊时只问一个问题

```
> 提示词

你想要哪类提示词？请描述一下具体需求（例如：客服助手、营销文案、代码审查）。
```

---

## 当前知识库

| 来源 | 提取数量 |
|------|---------|
| 姚金刚提示词合集 | 32 |
| AI营销_解压 | 16 |
| **合计** | **48** |

---

## License

MIT
