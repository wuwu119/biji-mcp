# tests/test_integration.py
"""集成测试 - 测试完整的工具调用流程"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from biji_mcp.server import create_server
from biji_mcp.config import DEFAULT_CONFIG_PATH


@pytest.fixture
def mock_config(tmp_path, monkeypatch):
    """创建临时配置文件"""
    config_data = {
        "knowledge_bases": {
            "测试库": {
                "token": "test-token",
                "topic_id": "kb_test",
                "description": "测试用知识库"
            }
        },
        "default": "测试库",
        "settings": {"default_top_k": 5, "timeout": 10}
    }
    config_file = tmp_path / ".biji-mcp" / "config.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(json.dumps(config_data, ensure_ascii=False))

    # 替换默认配置路径
    monkeypatch.setattr("biji_mcp.server.load_config",
                        lambda: __import__("biji_mcp.config", fromlist=["load_config"]).load_config(config_file))

    return config_file


class TestListKb:
    @pytest.mark.asyncio
    async def test_list_kb_returns_configured_kbs(self, mock_config):
        from biji_mcp.config import load_config
        config = load_config(mock_config)
        from biji_mcp.tools import format_kb_list

        result = format_kb_list(config)

        assert "测试库" in result
        assert "测试用知识库" in result
        assert "✓" in result


class TestSearchTool:
    @pytest.mark.asyncio
    async def test_search_formats_response(self, mock_config):
        from biji_mcp.client import BijiClient, SearchResult, Reference
        from biji_mcp.tools import format_search_result

        result = SearchResult(
            answer="这是测试答案",
            references=[Reference(title="测试来源", content="引用内容")],
        )

        output = format_search_result(result)

        assert "这是测试答案" in output
        assert "测试来源" in output


class TestRecallTool:
    @pytest.mark.asyncio
    async def test_recall_formats_response(self, mock_config):
        from biji_mcp.client import RecallResult
        from biji_mcp.tools import format_recall_results

        results = [
            RecallResult(
                id="1", title="测试笔记", content="笔记内容",
                score=0.95, type="NOTE", recall_source="embedding"
            )
        ]

        output = format_recall_results(results)

        assert "测试笔记" in output
        assert "0.95" in output
        assert "NOTE" in output
