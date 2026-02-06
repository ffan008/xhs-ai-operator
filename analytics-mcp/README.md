# Analytics MCP Server

小红书 AI 运营系统的数据分析和报告生成 MCP 服务器。

## 功能

- 分析笔记互动数据
- 生成详细的分析报告（Markdown/JSON/HTML）
- 按内容类型分析表现
- 分析最佳发布时间
- 对比不同时间段表现
- 生成 AI 优化建议
- 导出数据（CSV/JSON）

## 安装

```bash
cd ~/.refly/mcp-servers/analytics-mcp
pip install -r requirements.txt
```

## 配置

在 Claude Code 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "analytics-mcp": {
      "command": "python",
      "args": ["/Users/fans/.refly/mcp-servers/analytics-mcp/src/server.py"]
    }
  }
}
```

## 工具列表

### analyze_engagement
分析笔记互动指标

**参数**:
- `posts`: 笔记列表（包含浏览、点赞、评论等数据）
- `time_range`: 时间范围（可选）

**返回**:
- 总体互动数据
- 互动构成分析
- 最佳表现内容

### generate_report
生成综合分析报告

**参数**:
- `account_data`: 账号和笔记数据
- `report_type`: 报告类型（overview/detailed/trends/comparison）
- `format`: 输出格式（markdown/json/html）

**返回**:
- 完整的分析报告

### analyze_content_performance
按内容类型分析表现

**参数**:
- `posts`: 笔记列表
- `categorize_by`: 分类方式（tags/style/topic/custom）

**返回**:
- 各类型内容的表现数据

### analyze_time_patterns
分析发布时间规律

**参数**:
- `posts`: 笔记列表（包含发布时间）

**返回**:
- 最佳发布时段
- 最佳发布星期

### compare_periods
对比两个时间段的表现

**参数**:
- `period1`: 第一个时间段（包含笔记和标签）
- `period2`: 第二个时间段（包含笔记和标签）

**返回**:
- 两个时间段的对比数据

### get_recommendations
生成 AI 优化建议

**参数**:
- `analysis_result`: 其他工具生成的分析结果
- `focus_areas`: 关注领域（content/timing/engagement/growth/all）

**返回**:
- 针对性的优化建议

### export_data
导出数据

**参数**:
- `data`: 要导出的数据
- `format`: 格式（csv/json/excel）
- `filename`: 文件名（不含扩展名）

**返回**:
- 导出文件路径

## 使用示例

```python
# 分析互动数据
result = await analytics_mcp.analyze_engagement(posts)

# 生成报告
report = await analytics_mcp.generate_report(account_data, "detailed", "markdown")

# 获取建议
recommendations = await analytics_mcp.get_recommendations(analysis_result, ["all"])
```

## 数据存储

分析报告和历史数据保存在 `data/` 目录下。

## 许可证

MIT
