# prompt-engineering

提示词工程助手：从本地知识库检索相似提示词，若无匹配则按 LangGPT 格式生成结构化提示词。触发信号：(1) 用户说「帮我写/找/生成一个 XX 的提示词」；(2) 用户说「有没有 XX 相关的 prompt 模板」；(3) 用户说「给我一个 XX 助手的系统提示」。

## 意图路由表

| 用户意图信号 | 执行路径 |
|---|---|
| 有具体需求/主题（"帮我搜/找/生成 XX"） | 直接搜库 → 有结果展示摘要供选择，无结果自动生成 |
| 只说「提示词」但没具体主题 | 问一个问题：「你想要哪类提示词？」— 不问第二个 |
| 明确说「生成新的」/ 「不用搜了」 | 跳过搜库，直接 LangGPT 生成 |
| 明确说「看看有没有现成的」 | 只搜库，无结果时告知而不自动生成 |

## 工作流程

**Step 1 — 判断意图**
- 有具体主题 → 直接执行，不问
- 无主题 → 只问一句「你想要哪类提示词？」，等回答后执行

**Step 2 — 执行**
- 搜库有结果：展示最多 3 条摘要（标题 + 一句话描述），提示用户回复数字选择
- 搜库无结果：自动生成 LangGPT 格式提示词，无需用户再确认
- 用户选数字后：输出对应完整提示词

**Step 3 — 边界**
- **做**：提示词搜索、LangGPT 格式提示词生成
- **不做**：写业务代码、分析文档、回答商业问题、做内容诊断
- 超出范围直接说：「这超出我的范围。我只做提示词搜索和生成。」

## Actions

### `handle_request`（主入口）

用户的自然语言需求直接触发此 action。

**Parameters:**
- `query` (string, required): 用户的需求描述

**Tool Code:**

```tool_code
import subprocess
import os
import shlex

script_path = os.path.join(os.path.dirname(__file__), 'run.py')
quoted_query = shlex.quote(query.strip()) if query and query.strip() else '""'

print(default_api.exec(command=f"python3 {script_path} generate_prompt {quoted_query}"))
```

**Example:**

```python
handle_request(query="帮我生成一个关于 GEO 营销的提示词")
handle_request(query="找一个小红书文案助手的 prompt")
```

### `select_prompt`（选择提示词，用户回复数字后触发）

**Parameters:**
- `index` (integer, required): 用户选择的序号（1-based）

**Tool Code:**

```tool_code
import os
import shlex

script_path = os.path.join(os.path.dirname(__file__), 'run.py')
print(default_api.exec(command=f"python3 {script_path} select_prompt {shlex.quote(str(index))}"))
```

**Example:**

```python
select_prompt(index=2)
```
