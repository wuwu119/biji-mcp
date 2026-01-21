# Get笔记 MCP Server

在 Claude 中搜索 Get笔记 知识库内容。

## 安装

```bash
# 克隆项目
git clone <repo>
cd biji-mcp

# 安装依赖
uv sync
```

## 配置

首次运行会自动创建配置文件 `~/.biji-mcp/config.json`，请编辑填入你的API配置：

```json
{
  "knowledge_bases": {
    "工作": {
      "token": "your-api-token",
      "topic_id": "your-topic-id",
      "description": "工作相关笔记"
    }
  },
  "default": "工作",
  "settings": {
    "default_top_k": 10,
    "timeout": 30
  }
}
```

获取API配置：进入 Get笔记 Web版知识库 → 点击"API设置"按钮。

## Claude Desktop 配置

在 `~/Library/Application Support/Claude/claude_desktop_config.json` 添加：

```json
{
  "mcpServers": {
    "biji": {
      "command": "uv",
      "args": ["--directory", "/path/to/biji-mcp", "run", "biji-mcp"]
    }
  }
}
```

## 可用工具

### biji_search

在知识库中搜索，返回AI生成的答案。

参数：
- `question` (必需): 搜索问题
- `kb`: 知识库名称
- `deep_seek`: 启用深度思考
- `with_refs`: 返回引用来源

### biji_recall

召回原始内容片段，不经AI处理。

参数：
- `question` (必需): 搜索问题
- `kb`: 知识库名称
- `top_k`: 返回结果数量
- `intent_rewrite`: 意图改写

### biji_list_kb

列出已配置的知识库。

## 调试

设置环境变量启用调试日志：

```bash
BIJI_MCP_DEBUG=1 uv run biji-mcp
```

## API限制

- QPS: 2
- 日调用: 5000次
- 公测期免费
