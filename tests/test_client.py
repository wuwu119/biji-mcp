# tests/test_client.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from biji_mcp.client import BijiClient, RecallResult, BijiAPIError


class TestRecallResult:
    def test_from_api_response(self):
        api_data = {
            "id": "note_123",
            "title": "测试笔记",
            "content": "这是笔记内容",
            "score": 0.85,
            "type": "NOTE",
            "recall_source": "embedding",
        }
        result = RecallResult.from_api(api_data)

        assert result.id == "note_123"
        assert result.title == "测试笔记"
        assert result.content == "这是笔记内容"
        assert result.score == 0.85
        assert result.type == "NOTE"
        assert result.recall_source == "embedding"


class TestBijiClientRecall:
    @pytest.fixture
    def client(self):
        return BijiClient(token="test-token", timeout=30)

    @pytest.mark.asyncio
    async def test_recall_success(self, client):
        mock_response = {
            "code": 0,
            "data": {
                "results": [
                    {
                        "id": "n1",
                        "title": "笔记1",
                        "content": "内容1",
                        "score": 0.9,
                        "type": "NOTE",
                        "recall_source": "embedding",
                    },
                    {
                        "id": "n2",
                        "title": "笔记2",
                        "content": "内容2",
                        "score": 0.8,
                        "type": "FILE",
                        "recall_source": "keyword",
                    },
                ]
            }
        }

        with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await client.recall(
                question="测试问题",
                topic_id="kb_123",
                top_k=10,
            )

            assert len(results) == 2
            assert results[0].title == "笔记1"
            assert results[1].type == "FILE"

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/knowledge/search/recall"
            assert call_args[1]["json"]["question"] == "测试问题"

    @pytest.mark.asyncio
    async def test_recall_auth_error(self, client):
        with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = BijiAPIError(401, "Unauthorized")

            with pytest.raises(BijiAPIError) as exc_info:
                await client.recall("问题", "kb_123")

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_recall_rate_limit(self, client):
        with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = BijiAPIError(429, "Rate limited")

            with pytest.raises(BijiAPIError) as exc_info:
                await client.recall("问题", "kb_123")

            assert exc_info.value.status_code == 429
