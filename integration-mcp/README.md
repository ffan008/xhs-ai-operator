# Integration MCP Server

小红书 AI 运营系统的工作流协调器 MCP 服务器，负责协调多个 MCP 服务器执行复杂任务。

## 功能

- 执行预定义工作流（发布、创作、分析、批量）
- 创建自定义工作流
- 工作流状态监控
- 多 MCP 协调

## 预定义工作流

### 1. publish (一键发布)
自动生成内容并发布

**步骤**:
1. 生成内容（标题、正文、标签）
2. 生成配图
3. 发布笔记
4. 记录结果

### 2. create (AI 创作增强)
基于搜索和数据分析生成高质量内容

**步骤**:
1. 搜索相关资料
2. 分析热门内容
3. 基于搜索结果生成内容
4. 生成风格化配图
5. 展示预览
6. 用户确认后发布

### 3. analyze (数据分析)
分析笔记表现并生成优化建议

**步骤**:
1. 获取创作者数据
2. 分析互动数据
3. 生成分析报告
4. 生成优化建议

### 4. batch (批量操作)
批量生成和发布内容

**步骤**:
1. 创建任务队列
2. 并发生成内容（限流 3 并发）
3. 质量检查
4. 分时发布

## 安装

```bash
cd ~/.refly/mcp-servers/integration-mcp
pip install -r requirements.txt
```

## 配置

在 Claude Code 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "integration-mcp": {
      "command": "python",
      "args": ["/Users/fans/.refly/mcp-servers/integration-mcp/src/workflow.py"]
    }
  }
}
```

## 工具列表

### execute_workflow
执行工作流

**参数**:
- `workflow_name`: 工作流名称（publish/create/analyze/batch/custom）
- `params`: 工作流参数
  - `topic`: 内容主题
  - `style`: 内容风格
  - `count`: 数量（批量操作）
  - `time_range`: 时间范围（分析）
  - `custom_steps`: 自定义步骤

**返回**:
- 执行结果
- 各步骤状态
- 执行 ID

### create_workflow
创建自定义工作流

**参数**:
- `workflow_id`: 工作流 ID
- `workflow_name`: 工作流名称
- `description`: 描述
- `steps`: 步骤列表

### list_workflows
列出所有工作流

**参数**:
- `type`: 过滤类型（predefined/custom/all）

### get_workflow_status
获取工作流状态

**参数**:
- `workflow_id`: 工作流 ID

## 使用示例

### 执行发布工作流

```python
result = await integration_mcp.execute_workflow(
    "publish",
    {
        "topic": "春季穿搭推荐",
        "style": "lively"
    }
)
```

### 执行分析工作流

```python
result = await integration_mcp.execute_workflow(
    "analyze",
    {
        "time_range": {
            "start_date": "2025-01-01",
            "end_date": "2025-01-31"
        }
    }
)
```

### 创建自定义工作流

```python
result = await integration_mcp.create_workflow(
    "my_workflow",
    "我的工作流",
    "描述",
    [
        {
            "step": "search",
            "mcp": "tavily-remote",
            "tool": "search",
            "params": {"query": "搜索内容"}
        },
        {
            "step": "generate",
            "mcp": "llm",
            "tool": "generate",
            "params": {}
        }
    ]
)
```

## 工作流定义格式

```json
{
  "workflow_id": "unique_id",
  "workflow_name": "工作流名称",
  "description": "工作流描述",
  "steps": [
    {
      "step": "步骤名称",
      "mcp": "MCP 服务器名称",
      "tool": "工具名称",
      "params": {},
      "condition": "执行条件（可选）"
    }
  ]
}
```

## 集成的 MCP 服务器

- xiaohongshu-mcp: 小红书发布和数据获取
- stability-mcp: 图像生成
- tavily-remote: 内容搜索
- scheduler-mcp: 定时任务
- analytics-mcp: 数据分析
- integration-mcp: 工作流协调（自身）

## 注意事项

1. 此服务器是协调器，实际功能依赖其他 MCP 服务器
2. 需要同时配置其他 MCP 服务器才能完整工作
3. 自定义工作流会保存在 `config/workflows.json`

## 许可证

MIT
