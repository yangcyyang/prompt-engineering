#!/usr/bin/env python3
"""
run.py — prompt-engineering skill 交互式入口
支持：generate_prompt, list_prompts, select_prompt 动作
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# 添加当前目录到路径，以便导入 engine 模块
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from engine import search, build_index, count_indexed, DEFAULT_KB_PATHS, summarize_content

# 临时文件路径，用于保存搜索结果（在多次调用之间共享）
TEMP_RESULT_FILE = Path(tempfile.gettempdir()) / "prompt_engineering_last_results.json"

def ensure_index():
    """确保索引已建立"""
    if count_indexed() == 0:
        build_index(DEFAULT_KB_PATHS)
    else:
        build_index(DEFAULT_KB_PATHS)  # 自动检查 mtime

def save_results(results: list):
    """保存搜索结果到临时文件"""
    try:
        with open(TEMP_RESULT_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[警告] 无法保存结果：{e}")

def load_results() -> list:
    """从临时文件加载搜索结果"""
    try:
        if TEMP_RESULT_FILE.exists():
            with open(TEMP_RESULT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[警告] 无法加载结果：{e}")
    return []

def format_prompt_summary(idx: int, result: dict) -> str:
    """格式化提示词摘要"""
    title = result.get('title', '未命名')
    source = result.get('source', '未知来源')
    summary = summarize_content(result.get('content', ''), max_len=150)
    return f"{idx}. **{title}**（来源：{source}）\n   {summary}"

def list_prompts(query: str = None, top_k: int = 3) -> list:
    """
    列出相关提示词摘要
    如果提供了 query，则根据 query 搜索；否则列出所有
    """
    ensure_index()
    
    if query:
        results = search(query, top_k=top_k)
        save_results(results)  # 保存结果供后续 select 使用
    else:
        # 如果没有 query，列出所有（这里简化为搜索空字符串）
        results = search("", top_k=top_k)
        save_results(results)
    
    if not results:
        print("📭 未找到相关提示词。")
        return []
    
    print(f"\n🔍 找到 {len(results)} 个相关提示词：\n")
    for idx, r in enumerate(results, 1):
        print(format_prompt_summary(idx, r))
        print()
    
    print("💡 请回复数字 **1、2 或 3** 选择你想要的提示词，或回复 **0** 取消。\n")
    
    return results

def select_prompt(index: int) -> str:
    """
    根据索引选择并返回完整提示词
    index: 1-based 索引
    """
    results = load_results()
    
    if not results:
        return "[错误] 没有可用的提示词列表。请先调用 list_prompts 或 generate_prompt。"
    
    if index < 1 or index > len(results):
        return f"[错误] 无效的选择：{index}。有效范围是 1-{len(results)}。"
    
    result = results[index - 1]
    title = result.get('title', '未命名')
    content = result.get('content', '')
    
    output = f"\n✅ 你选择了：**{title}**\n"
    output += "=" * 50 + "\n\n"
    output += content.strip()
    output += "\n\n" + "=" * 50 + "\n"
    
    return output

def generate_prompt(query: str):
    """
    生成提示词的交互式流程：
    1. 搜库，有结果则展示摘要等待选择
    2. 无结果则自动生成 LangGPT 格式提示词
    """
    if not query or not query.strip():
        print("你想要哪类提示词？请描述一下具体需求（例如：客服助手、营销文案、代码审查）。")
        return

    print(f"\n📝 正在为你搜索与「{query}」相关的提示词...\n")

    results = list_prompts(query, top_k=3)

    if not results:
        from engine import generate_fallback
        print("\n📭 知识库中暂无匹配。已为你按 LangGPT 格式生成：\n")
        print("=" * 50)
        print(generate_fallback(query))
        print("=" * 50)
        print("\n💡 如需调整角色或目标，直接告诉我。")

    # 有结果时已在 list_prompts 中展示摘要并提示用户选数字

def main():
    if len(sys.argv) < 2:
        print("Usage: run.py <action> [args...]")
        print("\nActions:")
        print("  generate_prompt <query>  - 搜索并列出相关提示词")
        print("  list_prompts [query]     - 列出提示词摘要")
        print("  select_prompt <index>    - 选择并显示完整提示词（1-based）")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "generate_prompt":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        generate_prompt(query)
    
    elif action == "list_prompts":
        query = sys.argv[2] if len(sys.argv) > 2 else None
        list_prompts(query)
    
    elif action == "select_prompt":
        if len(sys.argv) < 3:
            print("[错误] 请提供选择索引。用法：select_prompt <index>")
            sys.exit(1)
        try:
            index = int(sys.argv[2])
            print(select_prompt(index))
        except ValueError:
            print(f"[错误] 无效的索引：{sys.argv[2]}")
            sys.exit(1)
    
    else:
        print(f"[错误] 未知动作：{action}")
        print("支持的动作：generate_prompt, list_prompts, select_prompt")
        sys.exit(1)

if __name__ == '__main__':
    main()
