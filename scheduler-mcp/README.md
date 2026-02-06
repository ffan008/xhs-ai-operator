# Scheduler MCP Server

小红书 AI 运营系统的定时任务调度 MCP 服务器。

## 功能

- 添加/删除定时任务
- 暂停/恢复任务
- 列出所有任务
- 更新任务配置
- 解析 cron 表达式

## 安装

```bash
cd ~/.refly/mcp-servers/scheduler-mcp
pip install -r requirements.txt
```

## 配置

在 Claude Code 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "scheduler-mcp": {
      "command": "python",
      "args": ["/Users/fans/.refly/mcp-servers/scheduler-mcp/src/server.py"]
    }
  }
}
```

## 工具列表

### add_job
添加新的定时任务

**参数**:
- `job_id`: 任务唯一标识
- `job_name`: 任务名称
- `cron_expression`: Cron 表达式
- `workflow`: 工作流类型 (publish/create/analyze/batch)
- `params`: 工作流参数
- `description`: 任务描述

### remove_job
删除定时任务

**参数**:
- `job_id`: 任务 ID

### list_jobs
列出所有任务

**参数**:
- `status`: 过滤状态 (active/paused/all)

### pause_job
暂停任务

**参数**:
- `job_id`: 任务 ID

### resume_job
恢复任务

**参数**:
- `job_id`: 任务 ID

### get_job_info
获取任务详情

**参数**:
- `job_id`: 任务 ID

### update_job
更新任务

**参数**:
- `job_id`: 任务 ID
- `cron_expression`: 新的 cron 表达式
- `params`: 新的参数
- `enabled`: 是否启用

### parse_cron
解析 cron 表达式

**参数**:
- `cron_expression`: Cron 表达式

## Cron 表达式格式

```
┌───────────── 分钟 (0 - 59)
│ ┌───────────── 小时 (0 - 23)
│ │ ┌───────────── 日期 (1 - 31)
│ │ │ ┌───────────── 月份 (1 - 12)
│ │ │ │ ┌───────────── 星期 (0 - 6，0 = 周日)
│ │ │ │ │
* * * * *
```

**示例**:
- `0 7 * * *` - 每天早上 7 点
- `0 */6 * * *` - 每 6 小时
- `0 9 * * 1-5` - 工作日早上 9 点
- `*/30 * * * *` - 每 30 分钟
- `0 9 1 * *` - 每月 1 号早上 9 点

## 数据存储

任务数据保存在 `data/jobs.json` 文件中。

## 许可证

MIT
