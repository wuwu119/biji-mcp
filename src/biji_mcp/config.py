"""配置加载和校验模块"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 默认配置文件路径
DEFAULT_CONFIG_PATH = Path.home() / ".biji-mcp" / "config.json"


class ConfigError(Exception):
    """配置相关错误"""
    pass


class KnowledgeBase(BaseModel):
    """知识库配置"""
    token: str
    topic_id: str
    description: Optional[str] = None


class Settings(BaseModel):
    """全局设置"""
    default_top_k: int = 10
    timeout: int = 30


class Config(BaseModel):
    """完整配置"""
    knowledge_bases: dict[str, KnowledgeBase]
    default: str
    settings: Settings = Field(default_factory=Settings)


EXAMPLE_CONFIG = {
    "knowledge_bases": {
        "工作": {
            "token": "your-api-token-here",
            "topic_id": "your-topic-id-here",
            "description": "工作相关笔记"
        }
    },
    "default": "工作",
    "settings": {
        "default_top_k": 10,
        "timeout": 30
    }
}


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径，默认为 ~/.biji-mcp/config.json

    Returns:
        Config: 配置对象

    Raises:
        ConfigError: 配置文件不存在、格式错误或校验失败
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    config_path = Path(config_path)

    if not config_path.exists():
        # 创建目录和示例配置
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(EXAMPLE_CONFIG, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        raise ConfigError(
            f"配置文件不存在，示例配置已创建: {config_path}\n"
            "请编辑配置文件填入你的API Token和知识库ID"
        )

    try:
        config_data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"配置文件格式错误: {e}")

    try:
        config = Config(**config_data)
    except Exception as e:
        raise ConfigError(f"配置校验失败: {e}")

    # 验证default指向存在的知识库
    if config.default not in config.knowledge_bases:
        available = ", ".join(config.knowledge_bases.keys())
        raise ConfigError(
            f"默认知识库 '{config.default}' 不存在，可用: {available}"
        )

    logger.debug(f"配置加载成功，知识库: {list(config.knowledge_bases.keys())}")
    return config


def find_knowledge_base(
    config: Config,
    name: Optional[str]
) -> tuple[str, KnowledgeBase]:
    """
    根据名称查找知识库

    Args:
        config: 配置对象
        name: 知识库名称，None则使用默认

    Returns:
        tuple[str, KnowledgeBase]: (知识库名称, 知识库配置)

    Raises:
        ConfigError: 未找到或匹配歧义
    """
    if name is None:
        name = config.default

    # 1. 精确匹配
    if name in config.knowledge_bases:
        return name, config.knowledge_bases[name]

    # 2. 模糊匹配（名称包含输入）
    matches = [
        (kb_name, kb)
        for kb_name, kb in config.knowledge_bases.items()
        if name in kb_name
    ]

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        names = ", ".join(m[0] for m in matches)
        raise ConfigError(f"知识库名称 '{name}' 匹配多个: {names}，请指定更精确的名称")

    # 3. 未找到
    available = ", ".join(config.knowledge_bases.keys())
    raise ConfigError(f"未找到知识库 '{name}'，可用: {available}")
