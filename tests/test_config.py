# tests/test_config.py
import pytest
import json
import tempfile
from pathlib import Path
from biji_mcp.config import (
    Config,
    KnowledgeBase,
    load_config,
    find_knowledge_base,
    ConfigError,
)


class TestKnowledgeBaseModel:
    def test_valid_knowledge_base(self):
        kb = KnowledgeBase(
            token="test-token",
            topic_id="kb_123",
            description="测试知识库",
        )
        assert kb.token == "test-token"
        assert kb.topic_id == "kb_123"
        assert kb.description == "测试知识库"

    def test_description_optional(self):
        kb = KnowledgeBase(token="test-token", topic_id="kb_123")
        assert kb.description is None


class TestConfigModel:
    def test_valid_config(self):
        config = Config(
            knowledge_bases={
                "工作": KnowledgeBase(token="t1", topic_id="kb_1"),
            },
            default="工作",
        )
        assert "工作" in config.knowledge_bases
        assert config.default == "工作"

    def test_default_settings(self):
        config = Config(
            knowledge_bases={"test": KnowledgeBase(token="t", topic_id="k")},
            default="test",
        )
        assert config.settings.default_top_k == 10
        assert config.settings.timeout == 30


class TestLoadConfig:
    def test_load_valid_config(self, tmp_path):
        config_data = {
            "knowledge_bases": {
                "工作": {"token": "t1", "topic_id": "kb_1", "description": "工作笔记"},
            },
            "default": "工作",
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data, ensure_ascii=False))

        config = load_config(config_file)
        assert config.default == "工作"
        assert config.knowledge_bases["工作"].token == "t1"

    def test_missing_config_creates_example(self, tmp_path):
        config_file = tmp_path / "nonexistent" / "config.json"

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)

        assert "示例配置已创建" in str(exc_info.value)
        assert config_file.exists()

    def test_invalid_json_raises_error(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("not valid json")

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)

        assert "配置文件格式错误" in str(exc_info.value)


class TestFindKnowledgeBase:
    @pytest.fixture
    def config(self):
        return Config(
            knowledge_bases={
                "工作": KnowledgeBase(token="t1", topic_id="kb_1"),
                "读书笔记": KnowledgeBase(token="t2", topic_id="kb_2"),
                "工作日志": KnowledgeBase(token="t3", topic_id="kb_3"),
            },
            default="工作",
        )

    def test_exact_match(self, config):
        name, kb = find_knowledge_base(config, "工作")
        assert name == "工作"
        assert kb.topic_id == "kb_1"

    def test_default_when_none(self, config):
        name, kb = find_knowledge_base(config, None)
        assert name == "工作"
        assert kb.topic_id == "kb_1"

    def test_fuzzy_match(self, config):
        name, kb = find_knowledge_base(config, "读书")
        assert name == "读书笔记"
        assert kb.topic_id == "kb_2"

    def test_ambiguous_fuzzy_raises(self):
        # 创建一个没有精确匹配的配置来测试歧义
        config = Config(
            knowledge_bases={
                "工作笔记": KnowledgeBase(token="t1", topic_id="kb_1"),
                "工作日志": KnowledgeBase(token="t2", topic_id="kb_2"),
            },
            default="工作笔记",
        )
        with pytest.raises(ConfigError) as exc_info:
            find_knowledge_base(config, "工作")  # 匹配 "工作笔记" 和 "工作日志"

        assert "匹配多个" in str(exc_info.value)

    def test_not_found_raises(self, config):
        with pytest.raises(ConfigError) as exc_info:
            find_knowledge_base(config, "不存在的库")

        assert "未找到知识库" in str(exc_info.value)
        assert "工作" in str(exc_info.value)  # 应该列出可用的知识库
