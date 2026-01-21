"""MCP工具定义和结果格式化"""

from __future__ import annotations

from biji_mcp.client import RecallResult, SearchResult
from biji_mcp.config import Config


def format_recall_results(results: list[RecallResult]) -> str:
    """格式化召回结果为Markdown"""
    if not results:
        return "## 召回结果 (共0条)\n\n未找到相关内容。"

    lines = [f"## 召回结果 (共{len(results)}条)\n"]

    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r.title} [{r.type}] 相关度: {r.score:.2f}")
        lines.append(r.content)
        lines.append("")

    return "\n".join(lines)


def format_search_result(result: SearchResult) -> str:
    """格式化搜索结果为Markdown"""
    lines = ["## 答案\n"]
    lines.append(result.answer)
    lines.append("")

    if result.references:
        lines.append("## 引用来源\n")
        for i, ref in enumerate(result.references, 1):
            lines.append(f"{i}. **{ref.title}** - \"{ref.content[:100]}{'...' if len(ref.content) > 100 else ''}\"")
        lines.append("")

    if result.thinking:
        lines.append("## 思考过程\n")
        lines.append(result.thinking)
        lines.append("")

    return "\n".join(lines)


def format_kb_list(config: Config) -> str:
    """格式化知识库列表为Markdown表格"""
    lines = ["## 已配置的知识库\n"]
    lines.append("| 名称 | 描述 | 默认 |")
    lines.append("|------|------|------|")

    for name, kb in config.knowledge_bases.items():
        is_default = "✓" if name == config.default else ""
        description = kb.description or "-"
        lines.append(f"| {name} | {description} | {is_default} |")

    return "\n".join(lines)
