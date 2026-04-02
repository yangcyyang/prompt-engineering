#!/usr/bin/env python3
"""
engine.py — prompt-engineering skill 主入口
"""

import sys
import argparse
from pathlib import Path

from indexer import build_index, DEFAULT_KB_PATHS
from retriever import search, count_indexed

SKILL_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "langgpt_default.md"


def read_template() -> str:
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_text(encoding="utf-8")
    return ""


def generate_fallback(query: str) -> str:
    template = read_template()
    if not template:
        # 内联兜底，不依赖外部模板文件
        clean_goal = query.replace("生成一个", "").replace("写一个", "").replace("帮我", "").strip()
        return f"# Role: AI 助手\n\n## Profile\n- Description: 专注于帮助用户完成以下任务：{clean_goal}\n\n## Goals\n- 准确理解并完成：{clean_goal}\n\n## Constraints\n- 专注于核心任务，不跑题\n- 不提供不确定的信息\n\n## Workflows\n1. 接收用户输入\n2. 分析并给出结构化回答\n3. 根据反馈迭代优化"

    # 从 query 提取关键词作为 Role 和 Goals 的素材
    role_guess = "AI 助手"
    if "客服" in query:
        role_guess = "专业客服代表"
    elif "销售" in query:
        role_guess = "资深销售顾问"
    elif "文案" in query or "写作" in query:
        role_guess = "内容创作专家"
    elif "代码" in query or "编程" in query or "开发" in query:
        role_guess = "全栈开发工程师"
    elif "分析" in query or "报告" in query:
        role_guess = "数据分析师"
    elif " teaching" in query.lower() or "教" in query or "助教" in query:
        role_guess = "教学专家"

    # 简单替换模板中的占位符
    result = template.replace("<UserQuery>", query)
    result = result.replace("<Role>", role_guess)
    result = result.replace("<Goal>", query.replace("生成一个", "").replace("写一个", "").replace("帮我", "").strip())

    return result


def summarize_content(content: str, max_len: int = 300) -> str:
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    # 优先找角色/任务描述
    summary = ""
    for line in lines[:15]:
        if any(k in line for k in ["角色", "Role", "任务", "Task", "你是一位", "你是一个"]):
            if len(line) > 10:
                summary = line
                break
    if not summary and lines:
        # 跳过代码块围栏，找真正的内容行
        for line in lines:
            if not line.startswith("```") and not line.startswith("~~~"):
                summary = line if len(line) < 200 else line[:200] + "..."
                break
    if len(summary) > max_len:
        summary = summary[:max_len] + "..."
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="提示词知识库检索 + LangGPT 生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 engine.py "客服"
  python3 engine.py "帮我写一个生成小红书文案的提示词"
        """
    )
    parser.add_argument("query", help="用户需求/检索关键词")
    parser.add_argument("--top-k", type=int, default=3, help="返回最相关的提示词数量（默认：3）")
    parser.add_argument("--reindex", action="store_true", help="强制重新索引")
    args = parser.parse_args()

    # 1. 确保索引存在
    if args.reindex or count_indexed() == 0:
        build_index(DEFAULT_KB_PATHS)
    else:
        build_index(DEFAULT_KB_PATHS)  # 自动检查 mtime

    # 2. 检索
    results = search(args.query, top_k=args.top_k)

    # 3. 输出
    print(f"# 查询：{args.query}\n")

    if results:
        print(f"🔍 从知识库中找到 {len(results)} 个相关提示词：\n")
        for idx, r in enumerate(results, 1):
            print(f"## {idx}. {r['title']}（来源：{r['source']}）")
            print(f"{summarize_content(r['content'])}\n")
            print("<details>")
            print("<summary>点击查看完整提示词</summary>")
            print("")
            print("```markdown")
            print(r["content"].strip())
            print("```")
            print("</details>\n")
    else:
        print("📭 知识库中暂无完全匹配的提示词。")
        print("\n---")
        print("📝 已根据你的需求生成一个 LangGPT 格式的结构化提示词：\n")
        print(generate_fallback(args.query))


if __name__ == "__main__":
    main()
