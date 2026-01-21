"""Get笔记 API 客户端"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator

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


@dataclass
class Reference:
    """引用来源"""
    title: str
    content: str

    @classmethod
    def from_api(cls, data: dict) -> Reference:
        return cls(
            title=data.get("title", ""),
            content=data.get("content", ""),
        )


@dataclass
class SearchResult:
    """搜索结果"""
    answer: str
    references: list[Reference] = field(default_factory=list)
    thinking: Optional[str] = None


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

    async def _stream_post(self, endpoint: str, **kwargs) -> AsyncIterator[str]:
        """发送流式POST请求，返回异步生成器"""
        url = f"{BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        if self._debug:
            logger.info(f"API流式请求: {endpoint}, body={kwargs.get('json')}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream("POST", url, headers=headers, **kwargs) as response:
                    if response.status_code == 401:
                        raise BijiAPIError(401, "Token无效，请检查配置")
                    elif response.status_code == 429:
                        raise BijiAPIError(429, "超出API调用限制(QPS=2)，请稍后重试")
                    elif response.status_code >= 400:
                        content = await response.aread()
                        raise BijiAPIError(response.status_code, content.decode())

                    async for line in response.aiter_lines():
                        if line:
                            yield line
            except httpx.TimeoutException:
                raise BijiAPIError(0, "请求超时，请稍后重试")
            except httpx.RequestError as e:
                raise BijiAPIError(0, f"网络错误: {e}")

    async def search(
        self,
        question: str,
        topic_id: str,
        deep_seek: bool = False,
        refs: bool = True,
    ) -> SearchResult:
        """
        知识库搜索（AI增强，流式）

        Args:
            question: 搜索问题
            topic_id: 知识库ID
            deep_seek: 是否启用深度思考
            refs: 是否返回引用

        Returns:
            SearchResult: 搜索结果
        """
        payload = {
            "question": question,
            "topic_ids": [topic_id],
            "deep_seek": deep_seek,
            "refs": refs,
        }

        answer_parts = []
        thinking_parts = []
        references = []

        async for line in self._stream_post("/knowledge/search/stream", json=payload):
            if not line.startswith("data: "):
                continue

            try:
                data = json.loads(line[6:])  # 去掉 "data: " 前缀
            except json.JSONDecodeError:
                continue

            msg_type = data.get("msg_type")

            if msg_type == 1:
                # 答案内容
                content = data.get("content", "")
                answer_parts.append(content)
                if self._debug:
                    logger.debug(f"答案片段: {content}")

            elif msg_type == 21:
                # 深度思考
                content = data.get("content", "")
                thinking_parts.append(content)
                if self._debug:
                    logger.debug(f"思考片段: {content}")

            elif msg_type == 105:
                # 引用数据
                refs_data = data.get("refs", [])
                for ref in refs_data:
                    references.append(Reference.from_api(ref))
                if self._debug:
                    logger.debug(f"引用: {len(refs_data)}条")

            elif msg_type == 3:
                # 完成
                if self._debug:
                    logger.debug("流式响应完成")
                break

        return SearchResult(
            answer="".join(answer_parts),
            references=references,
            thinking="".join(thinking_parts) if thinking_parts else None,
        )
