"""Get笔记 MCP Server 主入口"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from biji_mcp.config import load_config, find_knowledge_base, ConfigError
from biji_mcp.client import BijiClient, BijiAPIError
from biji_mcp.tools import format_recall_results, format_search_result, format_kb_list

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("BIJI_MCP_DEBUG") == "1" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def create_server() -> Server:
    """创建MCP Server实例"""
    server = Server("biji-mcp")

    # 加载配置
    try:
        config = load_config()
    except ConfigError as e:
        logger.error(f"配置加载失败: {e}")
        # 仍然创建server，但工具调用时会报错
        config = None

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """列出可用工具"""
        return [
            Tool(
                name="biji_search",
                description="在Get笔记知识库中搜索，返回AI生成的答案和引用来源",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "搜索问题",
                        },
                        "kb": {
                            "type": "string",
                            "description": "知识库名称（可选，默认使用配置的默认知识库）",
                        },
                        "deep_seek": {
                            "type": "boolean",
                            "description": "是否启用深度思考（可选，默认false）",
                            "default": False,
                        },
                        "with_refs": {
                            "type": "boolean",
                            "description": "是否返回引用来源（可选，默认true）",
                            "default": True,
                        },
                    },
                    "required": ["question"],
                },
            ),
            Tool(
                name="biji_recall",
                description="召回知识库原始内容片段，不经AI处理，返回相关度排序的结果列表",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "搜索问题",
                        },
                        "kb": {
                            "type": "string",
                            "description": "知识库名称（可选，默认使用配置的默认知识库）",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "返回结果数量（可选，默认10）",
                            "default": 10,
                        },
                        "intent_rewrite": {
                            "type": "boolean",
                            "description": "是否进行意图改写（可选，默认false）",
                            "default": False,
                        },
                    },
                    "required": ["question"],
                },
            ),
            Tool(
                name="biji_list_kb",
                description="列出所有已配置的Get笔记知识库",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """处理工具调用"""
        try:
            if config is None:
                raise ConfigError("配置未加载，请检查 ~/.biji-mcp/config.json")

            if name == "biji_list_kb":
                result = format_kb_list(config)
                return [TextContent(type="text", text=result)]

            # 获取知识库配置
            kb_name = arguments.get("kb")
            kb_name, kb = find_knowledge_base(config, kb_name)

            # 创建客户端
            client = BijiClient(token=kb.token, timeout=config.settings.timeout)

            if name == "biji_search":
                search_result = await client.search(
                    question=arguments["question"],
                    topic_id=kb.topic_id,
                    deep_seek=arguments.get("deep_seek", False),
                    refs=arguments.get("with_refs", True),
                )
                result = format_search_result(search_result)

            elif name == "biji_recall":
                recall_results = await client.recall(
                    question=arguments["question"],
                    topic_id=kb.topic_id,
                    top_k=arguments.get("top_k", config.settings.default_top_k),
                    intent_rewrite=arguments.get("intent_rewrite", False),
                )
                result = format_recall_results(recall_results)

            else:
                result = f"未知工具: {name}"

            return [TextContent(type="text", text=result)]

        except ConfigError as e:
            return [TextContent(type="text", text=f"配置错误: {e}")]
        except BijiAPIError as e:
            return [TextContent(type="text", text=f"API错误: {e}")]
        except Exception as e:
            logger.exception(f"工具调用异常: {e}")
            return [TextContent(type="text", text=f"内部错误: {e}")]

    return server


def main():
    """主入口"""
    server = create_server()

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
