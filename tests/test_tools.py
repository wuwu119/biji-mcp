# tests/test_tools.py
import pytest
from biji_mcp.client import RecallResult, SearchResult, Reference
from biji_mcp.tools import format_recall_results, format_search_result, format_kb_list
from biji_mcp.config import Config, KnowledgeBase


class TestFormatRecallResults:
    def test_formats_multiple_results(self):
        results = [
            RecallResult(
                id="1", title="笔记1", content="内容1",
                score=0.92, type="NOTE", recall_source="embedding"
            ),
            RecallResult(
                id="2", title="文件1", content="内容2",
                score=0.85, type="FILE", recall_source="keyword"
            ),
        ]
        output = format_recall_results(results)

        assert "召回结果" in output
        assert "共2条" in output
        assert "笔记1" in output
        assert "[NOTE]" in output
        assert "0.92" in output
        assert "文件1" in output
        assert "[FILE]" in output

    def test_empty_results(self):
        output = format_recall_results([])
        assert "未找到" in output or "0条" in output


class TestFormatSearchResult:
    def test_formats_with_refs(self):
        result = SearchResult(
            answer="这是AI生成的答案",
            references=[
                Reference(title="来源1", content="引用内容1"),
                Reference(title="来源2", content="引用内容2"),
            ],
        )
        output = format_search_result(result)

        assert "答案" in output
        assert "这是AI生成的答案" in output
        assert "引用来源" in output
        assert "来源1" in output
        assert "来源2" in output

    def test_formats_without_refs(self):
        result = SearchResult(answer="简单答案", references=[])
        output = format_search_result(result)

        assert "简单答案" in output


class TestFormatKbList:
    def test_formats_kb_list(self):
        config = Config(
            knowledge_bases={
                "工作": KnowledgeBase(token="t1", topic_id="k1", description="工作笔记"),
                "读书": KnowledgeBase(token="t2", topic_id="k2", description=None),
            },
            default="工作",
        )
        output = format_kb_list(config)

        assert "工作" in output
        assert "工作笔记" in output
        assert "读书" in output
        assert "✓" in output or "默认" in output
