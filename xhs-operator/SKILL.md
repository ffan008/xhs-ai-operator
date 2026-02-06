# 小红书 AI 运营系统 (Xiaohongshu AI Operator)

## 概述

这是一个 AI 驱动的小红书完整运营系统，通过 Claude Code 对话实现内容创作、发布、数据分析、定时发布等全套功能。

## 触发词

### 核心命令

1. **`/xhs 发布 [主题]`** - 一键发布笔记
   - 示例：`/xhs 发布 春天来了，樱花盛开`
   - 自动生成标题、正文、配图并发布

2. **`/xhs 创作 [主题] -风格 [风格]`** - AI 创作增强
   - 示例：`/xhs 创作 健康早餐 -风格 活泼`
   - 支持风格：活泼、专业、治愈、干货、种草

3. **`/xhs 分析 [时间范围]`** - 数据分析
   - 示例：`/xhs 分析 最近7天`
   - 示例：`/xhs 分析 2025-01-01至2025-01-31`

4. **`/xhs 定时 [cron表达式] [任务描述]`** - 定时发布
   - 示例：`/xhs 定时 "0 9 * * *" 每天早上9点发布早安内容`
   - 示例：`/xhs 定时 "0 */6 * * *" 每6小时发布一次`

5. **`/xhs 批量 [数量] [主题]`** - 批量操作
   - 示例：`/xhs 批量 5 春季穿搭推荐`
   - 自动分时发布，避免风控

### 辅助命令

6. **`/xhs 预览 [主题]`** - 预览内容（不发布）
7. **`/xhs 账号`** - 查看账号信息
8. **`/xhs 模板`** - 列出可用模板
9. **`/xhs 任务`** - 查看定时任务列表
10. **`/xhs 取消任务 [任务ID]`** - 取消定时任务

## 工作流

### 工作流 1: 一键发布 (publish)

```yaml
name: publish
description: 自动生成并发布小红书笔记
steps:
  1. parse_input:
      action: 解析用户输入的主题
      output: { topic, keywords }

  2. generate_content:
      action: 调用 content_generation prompt
      input: { topic, keywords }
      output: { title, body, tags }

  3. generate_image:
      action: 调用 stability-mcp 生成配图
      input: { topic, style: default }
      output: { image_url }

  4. publish:
      action: 调用 xiaohongshu-mcp 发布接口
      input: { title, body, tags, image_url }
      output: { post_id, post_url }

  5. report:
      action: 返回发布结果
      output: "✅ 发布成功！笔记链接: {post_url}"
```

### 工作流 2: AI 创作增强 (create)

```yaml
name: create
description: 基于搜索和数据分析生成高质量内容
steps:
  1. parse_input:
      action: 解析主题和风格
      output: { topic, style, keywords }

  2. search_content:
      action: 调用 tavily-remote 搜索相关资料
      input: { topic }
      output: { search_results }

  3. analyze_trends:
      action: 调用 xiaohongshu-mcp 分析热门内容
      input: { keywords }
      output: { trending_tags, popular_topics }

  4. generate_content:
      action: LLM 基于搜索结果生成原创内容
      input: { topic, style, search_results, trending_tags }
      output: { title, body, tags, draft_id }

  5. generate_image:
      action: stability-mcp 生成风格化配图
      input: { topic, style }
      output: { image_url }

  6. preview:
      action: 展示预览
      output: { title, body, tags, image_url }

  7. confirm_publish:
      action: 用户确认后发布
      input: { draft_id }
      output: { post_id, post_url }
```

### 工作流 3: 数据分析 (analyze)

```yaml
name: analyze
description: 分析笔记表现并生成优化建议
steps:
  1. parse_time_range:
      action: 解析时间范围
      output: { start_date, end_date }

  2. fetch_data:
      action: 调用 xiaohongshu-mcp 获取创作者数据
      input: { start_date, end_date }
      output: { posts, metrics, engagement_data }

  3. analyze_metrics:
      action: 调用 analytics-mcp 分析数据
      input: { posts, metrics, engagement_data }
      output: { analysis_result, insights }

  4. generate_recommendations:
      action: LLM 生成优化建议
      input: { analysis_result, insights }
      output: { recommendations, report }

  5. visualize:
      action: 生成可视化报告
      output: { charts, summary }
```

### 工作流 4: 定时发布 (schedule)

```yaml
name: schedule
description: 创建定时发布任务
steps:
  1. parse_cron:
      action: 解析 cron 表达式
      output: { cron_expression, schedule_info }

  2. create_task:
      action: 调用 scheduler-mcp 创建任务
      input: { cron_expression, task_description }
      output: { task_id }

  3. generate_content_pool:
      action: 生成内容池（多篇备选）
      input: { task_description }
      output: { content_pool }

  4. monitor:
      action: 设置任务监控
      output: { monitoring_config }

  5. confirm:
      action: 返回任务确认
      output: "✅ 定时任务已创建！任务ID: {task_id}"
```

### 工作流 5: 批量操作 (batch)

```yaml
name: batch
description: 批量生成和发布内容
steps:
  1. parse_input:
      action: 解析数量和主题
      output: { count, topic, keywords }

  2. create_queue:
      action: 创建任务队列
      output: { task_queue }

  3. parallel_generation:
      action: 并发生成内容（限流 3 并发）
      input: { task_queue, max_concurrent: 3 }
      output: { generated_content }

  4. quality_check:
      action: 质量检查（去重、长度验证）
      input: { generated_content }
      output: { validated_content }

  5. scheduled_publish:
      action: 分时发布（间隔 30 分钟）
      input: { validated_content, interval: 30min }
      output: { publish_schedule }

  6. progress_tracking:
      action: 进度追踪
      output: { progress_report }
```

## MCP 映射

### 使用的 MCP 服务器

| MCP 服务器 | 用途 | 相关工具 |
|-----------|------|---------|
| **xiaohongshu-mcp** | 小红书发布、数据获取 | `publish_note`, `get_creator_info`, `get_note_data` |
| **stability-mcp** | 图像生成 | `generate_image` |
| **tavily-remote** | 内容搜索 | `search` |
| **scheduler-mcp** | 定时任务 | `add_job`, `remove_job`, `list_jobs` |
| **analytics-mcp** | 数据分析 | `analyze_engagement`, `generate_report` |
| **integration-mcp** | 工作流协调 | `execute_workflow` |

### 工具调用映射

#### xiaohongshu-mcp
```python
# 发布笔记
publish_note(title: str, content: str, images: list, tags: list) -> dict

# 获取创作者信息
get_creator_info() -> dict

# 获取笔记数据
get_note_data(note_id: str) -> dict

# 搜索笔记
search_notes(query: str) -> list
```

#### stability-mcp
```python
# 生成图像
generate_image(prompt: str, aspect_ratio: str = "3:4") -> str
```

#### scheduler-mcp
```python
# 添加任务
add_job(cron: str, workflow: str, params: dict) -> str

# 移除任务
remove_job(job_id: str) -> bool

# 列出任务
list_jobs() -> list
```

#### analytics-mcp
```python
# 分析互动数据
analyze_engagement(posts: list) -> dict

# 生成报告
generate_report(analysis: dict) -> str
```

## Prompt 模板

### 内容生成模板
- 文件：`PROMPTS/content_generation.md`
- 用途：生成标题、正文、标签
- 支持风格：活泼、专业、治愈、干货、种草

### 图像生成模板
- 文件：`PROMPTS/image_generation.md`
- 用途：生成 3:4 比例的配图
- 支持风格：简约、插画、摄影、卡通

### 分析报告模板
- 文件：`PROMPTS/analysis_report.md`
- 用途：生成数据分析和优化建议
- 输出：结构化报告 + 可视化建议

## 配置文件

### 账号配置
- 文件：`CONFIG/accounts.json`
- 内容：小红书账号信息、登录凭证

### 内容模板
- 文件：`CONFIG/templates.json`
- 内容：预定义的内容模板（早安、干货、种草等）

### 定时任务配置
- 文件：`CONFIG/schedule.yaml`
- 内容：预设的定时任务配置

## 使用示例

### 示例 1: 快速发布
```
用户: /xhs 发布 春天来了，推荐3个赏花好去处

AI:
✅ 正在生成内容...

📝 标题：春日限定！这3个赏花秘境美到窒息🌸

📄 正文：
春天终于来啦！姐妹们，今天给你们分享3个私藏的赏花圣地...

🏷️ 标签：#春天 #赏花 #旅行推荐

🖼️ 正在生成配图...

✅ 配图生成完成！

📤 正在发布...

✅ 发布成功！
笔记链接：https://xiaohongshu.com/x/abc123
```

### 示例 2: 风格化创作
```
用户: /xhs 创作 10分钟健康早餐 -风格 治愈

AI:
🔍 正在搜索相关资料...

📊 正在分析热门内容...

✨ 内容生成中...

📝 标题：清晨10分钟，给自己一份温柔的营养🥣

📄 正文：
在这个快节奏的世界里，早晨的十分钟是属于你自己的慢时光...

🎨 风格：治愈系
🏷️ 标签：#早餐 #治愈系 #健康生活

🖼️ 正在生成治愈风格配图...

📋 内容预览：
[展示完整内容]

是否确认发布？(确认/修改)
```

### 示例 3: 数据分析
```
用户: /xhs 分析 最近7天

AI:
📊 正在获取数据...

📈 数据分析报告：

【整体表现】
- 发布笔记：5篇
- 总浏览量：12,345
- 总互动量：1,234
- 互动率：10.0%

【最佳表现】
🏆 最佳笔记：《春季穿搭技巧》
- 浏览量：5,678
- 点赞：456
- 收藏：234
- 评论：89

【优化建议】
1. 发布时间建议：晚上 8-10 点互动率最高
2. 内容方向：穿搭类内容表现最佳，建议增加
3. 标签优化：添加 #春季穿搭 #OOTD 等热门标签
4. 互动提升：在正文末尾增加提问，引导评论

【趋势预测】
根据近期数据，建议未来一周重点：
- 继续发布穿搭类内容
- 测试春季美妆内容
- 增加 before/after 对比内容
```

## 错误处理

### 常见错误及解决方案

1. **登录失败**
   - 检查 `accounts.json` 配置
   - 验证二维码登录状态
   - 解决方案：重新登录

2. **图像生成失败**
   - 检查 Stability AI API Key
   - 验证网络连接
   - 解决方案：使用备用图片或重试

3. **发布失败**
   - 检查内容长度（标题≤20字，正文≤1000字）
   - 验证图片格式和大小
   - 检查是否包含敏感词
   - 解决方案：调整内容后重试

4. **定时任务不执行**
   - 检查 cron 表达式格式
   - 验证 scheduler-mcp 服务状态
   - 解决方案：重启服务，检查日志

## 风控建议

### 发布频率限制
- 每小时 ≤ 10 篇
- 每天 ≤ 50 篇
- 批量发布间隔 ≥ 30 分钟

### 内容质量
- 原创性检查
- 敏感词过滤
- 重复内容检测

### 账号安全
- 使用官方 API 或 MCP
- 避免频繁登录/登出
- 监控账号状态

## 扩展功能

### 未来规划
- [ ] 多账号管理
- [ ] A/B 测试功能
- [ ] 数据导出（CSV/Excel）
- [ ] Web 管理界面
- [ ] 多平台支持（抖音、B站）
- [ ] AI 自主决策内容策略

## 技术栈

- **MCP 协议**：Model Context Protocol
- **Python**：3.9+
- **Node.js**：18+
- **APScheduler**：定时任务调度
- **Stability AI**：图像生成
- **Tavily**：内容搜索

## 维护指南

### 更新 MCP 服务器
```bash
cd ~/.refly/mcp-servers/xiaohongshu-mcp
git pull
docker compose restart
```

### 更新 Skill
```bash
# 编辑 PROMPTS 或 CONFIG 文件
# Claude Code 会自动重新加载
```

### 日志查看
```bash
# scheduler-mcp 日志
tail -f ~/.refly/mcp-servers/scheduler-mcp/logs/scheduler.log

# analytics-mcp 日志
tail -f ~/.refly/mcp-servers/analytics-mcp/logs/analytics.log
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请通过以下方式联系：
- GitHub Issues
- Email: [your-email]

---

**最后更新**: 2025-02-06
**版本**: 1.0.0
