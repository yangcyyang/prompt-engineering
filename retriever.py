#!/usr/bin/env python3
"""
retriever.py — SQLite FTS5 查询封装
"""

import re
import sqlite3
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
DB_PATH = SKILL_DIR / ".data" / "prompts_index.db"


def _tokenize_query(query: str) -> str:
    """
    对查询进行与 indexer 相同的切分：
    中文逐字，英文/数字保留单词，用 OR 连接。
    """
    raw_tokens = re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]", query)
    tokens = [t.lower() for t in raw_tokens if t.strip()]
    if not tokens:
        return query
    return " OR ".join(tokens)


def search(query: str, top_k: int = 3) -> list[dict]:
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 检查表是否存在
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='prompts_fts'"
    )
    if not cursor.fetchone():
        conn.close()
        return []

    fts_query = _tokenize_query(query)
    try:
        rows = cursor.execute(
            """
            SELECT m.title, m.content, m.source_path, rank
            FROM prompts_fts f
            JOIN prompts_meta m
              ON f.rowid = m.id
            WHERE f.prompts_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, top_k),
        ).fetchall()
    except sqlite3.OperationalError:
        # FTS5 语法错误时降级为直接 LIKE（在原始文本上）
        rows = cursor.execute(
            """
            SELECT title, content, source_path, 0 as rank
            FROM prompts_meta
            WHERE content LIKE ? OR title LIKE ?
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", top_k),
        ).fetchall()

    results = []
    for row in rows:
        results.append(
            {
                "title": row["title"],
                "content": row["content"],
                "source": Path(row["source_path"]).name,
                "rank": row["rank"],
            }
        )

    conn.close()
    return results


def count_indexed() -> int:
    if not DB_PATH.exists():
        return 0
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM prompts_meta")
    count = cursor.fetchone()[0]
    conn.close()
    return count
