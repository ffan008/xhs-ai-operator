#!/usr/bin/env python3
"""
小红书 AI 运营系统 - Scheduler MCP Server
基于 APScheduler 的定时任务调度服务器
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("scheduler-mcp")

# 任务存储路径
JOBS_FILE = Path(__file__).parent.parent / "data" / "jobs.json"


class SchedulerMCP:
    """Scheduler MCP 服务器"""

    def __init__(self):
        self.server = Server("scheduler-mcp")
        self.scheduler = None
        self.jobs = {}
        self._setup_scheduler()
        self._setup_handlers()

        # 确保数据目录存在
        JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 加载已保存的任务
        self._load_jobs()

    def _setup_scheduler(self):
        """设置 APScheduler"""
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 300
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Shanghai'
        )

        logger.info("APScheduler initialized")

    def _setup_handlers(self):
        """设置 MCP 处理器"""

        @self.server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            """列出可用资源"""
            return [
                Resource(
                    uri="scheduler://jobs",
                    name="Scheduled Jobs",
                    description="List of all scheduled jobs",
                    mimeType="application/json"
                ),
                Resource(
                    uri="scheduler://status",
                    name="Scheduler Status",
                    description="Current status of the scheduler",
                    mimeType="application/json"
                )
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """读取资源"""
            if uri == "scheduler://jobs":
                return json.dumps(self._get_all_jobs_info(), ensure_ascii=False, indent=2)
            elif uri == "scheduler://status":
                return json.dumps(self._get_scheduler_status(), ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """列出可用工具"""
            return [
                Tool(
                    name="add_job",
                    description="Add a new scheduled job",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Unique identifier for the job"
                            },
                            "job_name": {
                                "type": "string",
                                "description": "Human-readable name for the job"
                            },
                            "cron_expression": {
                                "type": "string",
                                "description": "Cron expression (e.g., '0 9 * * *' for 9 AM daily)"
                            },
                            "workflow": {
                                "type": "string",
                                "description": "Workflow to execute (publish, create, analyze, etc.)",
                                "enum": ["publish", "create", "analyze", "batch"]
                            },
                            "params": {
                                "type": "object",
                                "description": "Parameters for the workflow"
                            },
                            "description": {
                                "type": "string",
                                "description": "Job description"
                            }
                        },
                        "required": ["job_id", "job_name", "cron_expression", "workflow"]
                    }
                ),
                Tool(
                    name="remove_job",
                    description="Remove a scheduled job",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Job ID to remove"
                            }
                        },
                        "required": ["job_id"]
                    }
                ),
                Tool(
                    name="list_jobs",
                    description="List all scheduled jobs",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by status (active/paused/all)",
                                "enum": ["active", "paused", "all"],
                                "default": "all"
                            }
                        }
                    }
                ),
                Tool(
                    name="pause_job",
                    description="Pause a scheduled job",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Job ID to pause"
                            }
                        },
                        "required": ["job_id"]
                    }
                ),
                Tool(
                    name="resume_job",
                    description="Resume a paused job",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Job ID to resume"
                            }
                        },
                        "required": ["job_id"]
                    }
                ),
                Tool(
                    name="get_job_info",
                    description="Get detailed information about a specific job",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Job ID to query"
                            }
                        },
                        "required": ["job_id"]
                    }
                ),
                Tool(
                    name="update_job",
                    description="Update an existing job",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Job ID to update"
                            },
                            "cron_expression": {
                                "type": "string",
                                "description": "New cron expression"
                            },
                            "params": {
                                "type": "object",
                                "description": "New parameters"
                            },
                            "enabled": {
                                "type": "boolean",
                                "description": "Enable or disable the job"
                            }
                        },
                        "required": ["job_id"]
                    }
                ),
                Tool(
                    name="parse_cron",
                    description="Parse a cron expression and return human-readable description",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cron_expression": {
                                "type": "string",
                                "description": "Cron expression to parse"
                            }
                        },
                        "required": ["cron_expression"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
            """处理工具调用"""
            try:
                if name == "add_job":
                    result = await self._add_job(
                        arguments.get("job_id"),
                        arguments.get("job_name"),
                        arguments.get("cron_expression"),
                        arguments.get("workflow"),
                        arguments.get("params", {}),
                        arguments.get("description", "")
                    )
                elif name == "remove_job":
                    result = await self._remove_job(arguments.get("job_id"))
                elif name == "list_jobs":
                    result = await self._list_jobs(arguments.get("status", "all"))
                elif name == "pause_job":
                    result = await self._pause_job(arguments.get("job_id"))
                elif name == "resume_job":
                    result = await self._resume_job(arguments.get("job_id"))
                elif name == "get_job_info":
                    result = await self._get_job_info(arguments.get("job_id"))
                elif name == "update_job":
                    result = await self._update_job(
                        arguments.get("job_id"),
                        arguments.get("cron_expression"),
                        arguments.get("params"),
                        arguments.get("enabled")
                    )
                elif name == "parse_cron":
                    result = self._parse_cron(arguments.get("cron_expression"))
                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(type="text", text=json.dumps({
                    "error": str(e),
                    "tool": name
                }, ensure_ascii=False, indent=2))]

    def _load_jobs(self):
        """从文件加载任务"""
        if JOBS_FILE.exists():
            try:
                with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                    saved_jobs = json.load(f)
                    for job_data in saved_jobs:
                        job_id = job_data.get("job_id")
                        if job_id and job_data.get("enabled", True):
                            self._schedule_job(job_data)
                    self.jobs = {j.get("job_id"): j for j in saved_jobs}
                logger.info(f"Loaded {len(self.jobs)} jobs from file")
            except Exception as e:
                logger.error(f"Error loading jobs: {e}")

    def _save_jobs(self):
        """保存任务到文件"""
        try:
            with open(JOBS_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(self.jobs.values()), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving jobs: {e}")

    def _schedule_job(self, job_data: Dict[str, Any]):
        """调度单个任务"""
        job_id = job_data["job_id"]
        cron_expr = job_data["cron_expression"]

        # 解析 cron 表达式
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expr}")

        minute, hour, day, month, day_of_week = parts

        # 创建触发器
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone='Asia/Shanghai'
        )

        # 添加任务到调度器
        self.scheduler.add_job(
            self._execute_job,
            trigger=trigger,
            id=job_id,
            args=[job_data],
            name=job_data.get("job_name", job_id)
        )

        logger.info(f"Scheduled job: {job_id} with cron: {cron_expr}")

    async def _execute_job(self, job_data: Dict[str, Any]):
        """执行任务"""
        job_id = job_data["job_id"]
        workflow = job_data["workflow"]
        params = job_data.get("params", {})

        logger.info(f"Executing job {job_id}: {workflow}")

        # 这里应该调用相应的 workflow
        # 实际实现需要通过 integration-mcp 来协调
        # 目前只记录日志
        logger.info(f"Job {job_id} executed with params: {params}")

        # TODO: 发送通知给 integration-mcp 执行实际工作流

    def _get_all_jobs_info(self) -> List[Dict[str, Any]]:
        """获取所有任务信息"""
        jobs_info = []
        for job_id, job_data in self.jobs.items():
            info = {
                "job_id": job_id,
                "job_name": job_data.get("job_name"),
                "cron_expression": job_data.get("cron_expression"),
                "workflow": job_data.get("workflow"),
                "enabled": job_data.get("enabled", True),
                "description": job_data.get("description", ""),
                "next_run_time": None,
                "status": "paused"
            }

            # 从调度器获取运行时信息
            job = self.scheduler.get_job(job_id)
            if job:
                info["next_run_time"] = job.next_run_time.isoformat() if job.next_run_time else None
                info["status"] = "active" if job.next_run_time else "paused"

            jobs_info.append(info)

        return jobs_info

    def _get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "running": self.scheduler.running,
            "total_jobs": len(self.scheduler.get_jobs()),
            "active_jobs": len([j for j in self.scheduler.get_jobs() if j.next_run_time]),
            "timezone": str(self.scheduler.timezone),
            "start_time": datetime.now().isoformat()
        }

    async def _add_job(self, job_id: str, job_name: str, cron_expression: str,
                       workflow: str, params: dict, description: str) -> Dict[str, Any]:
        """添加新任务"""
        if job_id in self.jobs:
            raise ValueError(f"Job ID {job_id} already exists")

        job_data = {
            "job_id": job_id,
            "job_name": job_name,
            "cron_expression": cron_expression,
            "workflow": workflow,
            "params": params,
            "description": description,
            "enabled": True,
            "created_at": datetime.now().isoformat()
        }

        # 保存到内存
        self.jobs[job_id] = job_data

        # 添加到调度器
        self._schedule_job(job_data)

        # 保存到文件
        self._save_jobs()

        logger.info(f"Added job: {job_id}")

        return {
            "success": True,
            "message": f"Job {job_id} added successfully",
            "job": job_data
        }

    async def _remove_job(self, job_id: str) -> Dict[str, Any]:
        """删除任务"""
        if job_id not in self.jobs:
            raise ValueError(f"Job ID {job_id} not found")

        # 从调度器移除
        self.scheduler.remove_job(job_id)

        # 从内存移除
        del self.jobs[job_id]

        # 保存到文件
        self._save_jobs()

        logger.info(f"Removed job: {job_id}")

        return {
            "success": True,
            "message": f"Job {job_id} removed successfully"
        }

    async def _list_jobs(self, status: str = "all") -> Dict[str, Any]:
        """列出任务"""
        jobs = self._get_all_jobs_info()

        if status != "all":
            jobs = [j for j in jobs if j["status"] == status]

        return {
            "success": True,
            "count": len(jobs),
            "jobs": jobs
        }

    async def _pause_job(self, job_id: str) -> Dict[str, Any]:
        """暂停任务"""
        if job_id not in self.jobs:
            raise ValueError(f"Job ID {job_id} not found")

        self.scheduler.pause_job(job_id)
        self.jobs[job_id]["enabled"] = False
        self._save_jobs()

        logger.info(f"Paused job: {job_id}")

        return {
            "success": True,
            "message": f"Job {job_id} paused successfully"
        }

    async def _resume_job(self, job_id: str) -> Dict[str, Any]:
        """恢复任务"""
        if job_id not in self.jobs:
            raise ValueError(f"Job ID {job_id} not found")

        self.scheduler.resume_job(job_id)
        self.jobs[job_id]["enabled"] = True
        self._save_jobs()

        logger.info(f"Resumed job: {job_id}")

        return {
            "success": True,
            "message": f"Job {job_id} resumed successfully"
        }

    async def _get_job_info(self, job_id: str) -> Dict[str, Any]:
        """获取任务详情"""
        if job_id not in self.jobs:
            raise ValueError(f"Job ID {job_id} not found")

        job_data = self.jobs[job_id].copy()

        # 添加运行时信息
        job = self.scheduler.get_job(job_id)
        if job:
            job_data["next_run_time"] = job.next_run_time.isoformat() if job.next_run_time else None
            job_data["status"] = "active" if job.next_run_time else "paused"
        else:
            job_data["status"] = "unknown"

        return {
            "success": True,
            "job": job_data
        }

    async def _update_job(self, job_id: str, cron_expression: str = None,
                          params: dict = None, enabled: bool = None) -> Dict[str, Any]:
        """更新任务"""
        if job_id not in self.jobs:
            raise ValueError(f"Job ID {job_id} not found")

        # 更新字段
        if cron_expression:
            self.jobs[job_id]["cron_expression"] = cron_expression
            # 重新调度
            self.scheduler.remove_job(job_id)
            self._schedule_job(self.jobs[job_id])

        if params:
            self.jobs[job_id]["params"].update(params)

        if enabled is not None:
            self.jobs[job_id]["enabled"] = enabled
            if enabled:
                self.scheduler.resume_job(job_id)
            else:
                self.scheduler.pause_job(job_id)

        self.jobs[job_id]["updated_at"] = datetime.now().isoformat()
        self._save_jobs()

        logger.info(f"Updated job: {job_id}")

        return {
            "success": True,
            "message": f"Job {job_id} updated successfully",
            "job": self.jobs[job_id]
        }

    def _parse_cron(self, cron_expression: str) -> Dict[str, Any]:
        """解析 cron 表达式"""
        try:
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError("Invalid cron expression")

            minute, hour, day, month, day_of_week = parts

            # 简单描述生成
            descriptions = []

            # 分钟
            if minute == "*":
                descriptions.append("每分钟")
            elif minute.isdigit():
                descriptions.append(f"第{minute}分钟")
            elif "/" in minute:
                interval = minute.split("/")[1]
                descriptions.append(f"每{interval}分钟")

            # 小时
            if hour == "*":
                pass
            elif hour.isdigit():
                descriptions.append(f"{hour}点")
            elif "," in hour:
                hours = hour.split(",")
                descriptions.append(f"{','.join(hours)}点")

            # 日期
            if day == "*":
                pass
            elif day.isdigit():
                descriptions.append(f"每月{day}号")

            # 月份
            if month == "*":
                pass
            elif month.isdigit():
                descriptions.append(f"{month}月")

            # 星期
            if day_of_week == "*":
                pass
            elif day_of_week.isdigit():
                weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
                descriptions.append(weekdays[int(day_of_week)])

            description = " ".join(descriptions) if descriptions else "按计划执行"

            return {
                "success": True,
                "cron_expression": cron_expression,
                "description": description,
                "parsed": {
                    "minute": minute,
                    "hour": hour,
                    "day": day,
                    "month": month,
                    "day_of_week": day_of_week
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def run(self):
        """启动服务器"""
        # 启动调度器
        self.scheduler.start()
        logger.info("Scheduler started")

        # 运行 MCP 服务器
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="scheduler-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )


async def main():
    """主函数"""
    scheduler_mcp = SchedulerMCP()
    await scheduler_mcp.run()


if __name__ == "__main__":
    asyncio.run(main())
