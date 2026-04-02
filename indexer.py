#!/usr/bin/env python3
"""
indexer.py — 从两个 Markdown 知识库中提取提示词并建立 SQLite FTS5 索引
"""

import os
import re
import sqlite3
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).resolve().parent
DATA_DIR = SKILL_DIR / ".data"
DB_PATH = DATA_DIR / "prompts_index.db"

# 默认知识库路径
DEFAULT_KB_PATHS = [
    "/Users/cy/Documents/03 life/AI design/OrbitOS-CN/00_收件箱/姚金刚提示词合集/姚金刚提示词合集.md",
    "/Users/cy/Documents/03 life/AI design/OrbitOS-CN/00_收件箱/AI营销_解压/AI营销_解压.md",
]

# 正负面清单（H1标题）
PROMPT_KEYWORDS = re.compile(r'提示词|Prompt|生成器|助手|专家|元提示词|系统\s*v|模板')
DOC1_DENYLIST = re.compile(
    r'^# (角色|任务|格式|输出格式|工作流程|【Role|文章反编译|过度冗长惩罚|工具|有效通道|'
    r'指示|Penalty|Tools|The|Valid|Instructions|\[TRANSCENDENT_ROLE\]|\[超级GEO内容架构师\]|'
    r'\[标题：|\[优化后标题\])'
)
DOC2_DENYLIST = re.compile(
    r'^# (\[公司名称\]|\[行业\]|\[内容标题\]|\[业务领域\]|\[内容类型\]|\[行业名称\]|'
    r'\[主题\]|\[优化后|\[查询问题\])'
)


def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def sanitize_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name[:80] or "未命名"


def tokenize_for_fts(text: str) -> str:
    """
    为 FTS5 unicode61 做中文兼容切分：
    中文字符逐字拆分，英文/数字保留完整单词，其余忽略。
    """
    tokens = re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]", text)
    return " ".join(t.lower() for t in tokens)


def init_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            path TEXT PRIMARY KEY,
            mtime REAL,
            indexed_at TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS prompts_fts USING fts5(
            title, content, source_path, tokenize='unicode61'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prompts_meta (
            id INTEGER PRIMARY KEY,
            source_path TEXT,
            title TEXT,
            content TEXT,
            chunk_hash TEXT,
            indexed_at TEXT
        )
    """)
    conn.commit()
    return conn


def is_prompt_h1(line: str, doc_name: str) -> bool:
    """判断一个 # 标题是否是提示词的起始点。"""
    if not line.startswith("# "):
        return False
    has_kw = bool(PROMPT_KEYWORDS.search(line))
    if doc_name == "AI营销_解压.md":
        if not has_kw and DOC2_DENYLIST.match(line):
            return False
        return has_kw
    else:  # 姚金刚提示词合集.md
        if not has_kw and DOC1_DENYLIST.match(line):
            return False
        return has_kw


def find_nearest_heading(lines, start_idx) -> str:
    """向前查找最近的 # / ## / ### / #### 标题作为备用名称。"""
    for k in range(start_idx - 1, max(-1, start_idx - 30), -1):
        if re.match(r'^#{1,4} ', lines[k]):
            return lines[k].strip().lstrip("#").strip()
    return "未命名提示词"


def has_prompt_marker(lines, start_idx, window: int = 5) -> bool:
    """检查 start_idx 前 window 行内是否有 '提示词：' 标记。"""
    for k in range(start_idx - 1, max(-1, start_idx - window), -1):
        if "提示词：" in lines[k] or "提示词:" in lines[k]:
            return True
    return False


def is_codeblock_prompt(lines, start_idx, doc_name: str = "") -> tuple[bool, str]:
    """
    检查 ```markdown / ````markdown 块是否是一个有效提示词。
    返回 (is_valid, inferred_title)
    """
    end_idx = None
    fence = lines[start_idx].strip()
    close_fence = "```" if fence.startswith("```") else "````"
    for j in range(start_idx + 1, len(lines)):
        if lines[j].strip() == close_fence:
            end_idx = j
            break
    if end_idx is None:
        end_idx = min(start_idx + 100, len(lines))

    block_text = "".join(lines[start_idx:end_idx])
    has_rtf = bool(re.search(r'(角色|Role|任务|Task|R:|T:)', block_text[:1000]))
    if not has_rtf:
        return False, ""

    # 获取代码块内的第一个 #/## 标题
    first_heading = ""
    for k in range(start_idx + 1, end_idx):
        stripped = lines[k].strip()
        if re.match(r'^#{1,2} ', stripped):
            first_heading = stripped
            break

    # 过滤明显的输出模板代码块
    if first_heading and re.match(
        r'^#{1,2} (\[公司名称\]|\[行业\]|\[内容标题\]|\[业务领域\]|'
        r'\[行业名称\]|\[主题\]|\[查询问题\]|\[优化后)',
        first_heading
    ):
        return False, ""

    # 优先使用代码块内部的标题
    if first_heading and not re.match(
        r'^#{1,2} (\[公司名称\]|\[行业\]|\[内容标题\]|\[业务领域\]|'
        r'\[行业名称\]|\[主题\]|\[查询问题\]|\[优化后)',
        first_heading
    ):
        title = first_heading.lstrip("#").strip()
    else:
        title = find_nearest_heading(lines, start_idx)

    # 过滤姚金刚文档末尾的 canmore 工具块等特殊结构
    if title and re.match(
        r'^#{1,4} (文章反编译|过度冗长惩罚|工具|有效通道|指示|'
        r'Penalty|Tools|The|Valid|Instructions)',
        title
    ):
        return False, ""

    return True, title


def extract_prompts_from_lines(lines: list[str], doc_name: str, source_path: str) -> list[dict]:
    """核心提取逻辑：返回 [{title, content, source, start_line}]"""
    prompts = []
    n = len(lines)

    # 预扫描所有 H1 位置和 markdown 块
    h1_positions = []
    markdown_blocks = []
    for idx, line in enumerate(lines):
        if line.startswith("# ") and not line.startswith("## "):
            h1_positions.append(idx)
        stripped = line.strip()
        if stripped in ("```markdown", "````markdown"):
            fence = stripped
            close = "```" if fence.startswith("```") else "````"
            end = None
            for j in range(idx + 1, n):
                if lines[j].strip() == close:
                    end = j
                    break
            if end is None:
                end = min(idx + 100, n)
            markdown_blocks.append((idx, end))

    # Step 1: 提取所有独立的 markdown 代码块提示词
    extracted_mbs = set()
    for mb_start, mb_end in markdown_blocks:
        if (mb_start, mb_end) in extracted_mbs:
            continue

        valid, inferred_title = is_codeblock_prompt(lines, mb_start)
        if not valid:
            continue

        content = "".join(lines[mb_start:mb_end + 1])
        prompts.append({
            "title": inferred_title,
            "content": content,
            "source": source_path,
            "start_line": mb_start + 1,
        })
        extracted_mbs.add((mb_start, mb_end))

    # Step 2: 提取没有代码块包裹的 H1 提示词
    for i, h1_idx in enumerate(h1_positions):
        title_line = lines[h1_idx].rstrip('\n')
        if not is_prompt_h1(title_line, doc_name):
            continue

        # 如果该 H1 已经在某个已提取的代码块内部，跳过（避免重复）
        in_codeblock = False
        for mb_start, mb_end in markdown_blocks:
            if mb_start <= h1_idx < mb_end:
                in_codeblock = True
                break
        if in_codeblock:
            continue

        end_idx = h1_positions[i + 1] if i + 1 < len(h1_positions) else n
        content = "".join(lines[h1_idx:end_idx])
        prompts.append({
            "title": title_line[2:].strip(),
            "content": content,
            "source": source_path,
            "start_line": h1_idx + 1,
        })

    # 按行号排序并去重
    prompts.sort(key=lambda x: x["start_line"])
    seen = set()
    unique_prompts = []
    for p in prompts:
        key = (p["title"], p["start_line"])
        if key not in seen:
            seen.add(key)
            unique_prompts.append(p)

    return unique_prompts


def build_index(kb_paths=None):
    if kb_paths is None:
        kb_paths = DEFAULT_KB_PATHS

    conn = init_db()
    cursor = conn.cursor()

    for path_str in kb_paths:
        path = Path(path_str).expanduser().resolve()
        if not path.exists():
            print(f"⚠️  知识库不存在，跳过: {path}")
            continue

        mtime = path.stat().st_mtime
        doc_name = path.name

        # 检查是否需要重新索引
        row = cursor.execute(
            "SELECT mtime FROM sources WHERE path = ?", (str(path),)
        ).fetchone()

        if row and row[0] >= mtime:
            print(f"✅ 索引已是最新: {doc_name}")
            continue

        print(f"🔄 重新索引: {doc_name}")

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        prompts = extract_prompts_from_lines(lines, doc_name, str(path))
        print(f"   提取到 {len(prompts)} 个提示词")

        # 导出为独立 .md 文件
        source_slug = Path(doc_name).stem
        export_dir = SKILL_DIR / "prompts" / source_slug
        if export_dir.exists():
            shutil.rmtree(export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
        for idx, p in enumerate(prompts, start=1):
            safe_title = sanitize_filename(p["title"])
            filename = f"{idx:03d}_{safe_title}.md"
            front = (
                f"---\n"
                f"title: {p['title']}\n"
                f"source: {p['source']}\n"
                f"line: {p['start_line']}\n"
                f"---\n\n"
            )
            (export_dir / filename).write_text(front + p["content"], encoding="utf-8")
        print(f"   导出到: {export_dir}")

        # 删除旧数据
        cursor.execute("DELETE FROM prompts_fts WHERE source_path = ?", (str(path),))
        cursor.execute("DELETE FROM prompts_meta WHERE source_path = ?", (str(path),))

        for p in prompts:
            cursor.execute(
                "INSERT INTO prompts_fts (title, content, source_path) VALUES (?, ?, ?)",
                (tokenize_for_fts(p["title"]), tokenize_for_fts(p["content"]), p["source"]),
            )
            cursor.execute(
                """
                INSERT INTO prompts_meta (source_path, title, content, chunk_hash, indexed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    p["source"],
                    p["title"],
                    p["content"],
                    md5(p["content"]),
                    datetime.now().isoformat(),
                ),
            )

        cursor.execute(
            """
            INSERT INTO sources (path, mtime, indexed_at)
            VALUES (?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET mtime=excluded.mtime, indexed_at=excluded.indexed_at
            """,
            (str(path), mtime, datetime.now().isoformat()),
        )
        conn.commit()

    conn.close()
    print(f"\n📁 索引文件: {DB_PATH}")


if __name__ == "__main__":
    build_index()
