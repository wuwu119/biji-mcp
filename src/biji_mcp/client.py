"""Get笔记 API 客户端"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://open-api.biji.com/getnote/openapi"


class BijiAPIError(Exception):
    """API调用错误"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")


@dataclass
class RecallResult:
    """召回结果"""
    id: str
    title: str
    content: str
    score: float
    type: str  # NOTE, FILE, BLOGGER
    recall_source: str  # embedding, keyword

    @classmethod
    def from_api(cls, data: dict) -> RecallResult:
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            score=data.get("score", 0.0),
            type=data.get("type", "NOTE"),
            recall_source=data.get("recall_source", ""),
        )


class BijiClient:
    """Get笔记 API 客户端"""

    def __init__(self, token: str, timeout: int = 30):
        self.token = token
        self.timeout = timeout
        self._debug = os.environ.get("BIJI_MCP_DEBUG") == "1"

    async def _post(self, endpoint: str, **kwargs) -> dict:
        """发送POST请求"""
        url = f"{BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        if self._debug:
            logger.info(f"API请求: {endpoint}, body={kwargs.get('json')}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, headers=headers, **kwargs)
            except httpx.TimeoutException:
                raise BijiAPIError(0, "请求超时，请稍后重试")
            except httpx.RequestError as e:
                raise BijiAPIError(0, f"网络错误: {e}")

            if response.status_code == 401:
                raise BijiAPIError(401, "Token无效，请检查配置")
            elif response.status_code == 429:
                raise BijiAPIError(429, "超出API调用限制(QPS=2)，请稍后重试")
            elif response.status_code >= 400:
                raise BijiAPIError(response.status_code, response.text)

            data = response.json()

            if self._debug:
                logger.info(f"API响应: {data}")

            return data

    async def recall(
        self,
        question: str,
        topic_id: str,
        top_k: int = 10,
        intent_rewrite: bool = False,
        select_matrix: bool = False,
    ) -> list[RecallResult]:
        """
        知识库召回（原始结果）

        Args:
            question: 搜索问题
            topic_id: 知识库ID
            top_k: 返回结果数量
            intent_rewrite: 是否进行意图改写
            select_matrix: 是否进行结果重选

        Returns:
            list[RecallResult]: 召回结果列表
        """
        payload = {
            "question": question,
            "topic_ids": [topic_id],
            "top_k": top_k,
            "intent_rewrite": intent_rewrite,
            "select_matrix": select_matrix,
        }

        response = await self._post("/knowledge/search/recall", json=payload)

        results = []
        if "data" in response and "results" in response["data"]:
            for item in response["data"]["results"]:
                results.append(RecallResult.from_api(item))

        return results
