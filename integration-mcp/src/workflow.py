#!/usr/bin/env python3
"""
小红书 AI 运营系统 - Integration MCP Server
工作流协调器，协调多个 MCP 服务器执行复杂任务
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("integration-mcp")

# 配置文件路径
CONFIG_DIR = Path(__file__).parent.parent / "config"
WORKFLOWS_FILE = CONFIG_DIR / "workflows.json"


class IntegrationMCP:
    """Integration MCP 服务器 - 工作流协调器"""

    def __init__(self):
        self.server = Server("integration-mcp")
        self.workflows = {}
        self._setup_handlers()

        # 加载工作流配置
        self._load_workflows()

    def _setup_handlers(self):
        """设置 MCP 处理器"""

        @self.server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            """列出可用资源"""
            return [
                Resource(
                    uri="integration://workflows",
                    name="Workflows",
                    description="Available workflows",
                    mimeType="application/json"
                ),
                Resource(
                    uri="integration://status",
                    name="Integration Status",
                    description="Status of integrated services",
                    mimeType="application/json"
                )
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """读取资源"""
            if uri == "integration://workflows":
                return json.dumps(self.workflows, ensure_ascii=False, indent=2)
            elif uri == "integration://status":
                return json.dumps(self._get_status(), ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """列出可用工具"""
            return [
                Tool(
                    name="execute_workflow",
                    description="Execute a predefined workflow or custom workflow",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_name": {
                                "type": "string",
                                "description": "Name of the workflow to execute",
                                "enum": ["publish", "create", "analyze", "batch", "custom"]
                            },
                            "params": {
                                "type": "object",
                                "description": "Parameters for the workflow",
                                "properties": {
                                    "topic": {
                                        "type": "string",
                                        "description": "Content topic"
                                    },
                                    "style": {
                                        "type": "string",
                                        "description": "Content style"
                                    },
                                    "count": {
                                        "type": "number",
                                        "description": "Number of items (for batch)"
                                    },
                                    "time_range": {
                                        "type": "object",
                                        "description": "Time range for analysis"
                                    },
                                    "custom_steps": {
                                        "type": "array",
                                        "description": "Custom workflow steps",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "step": {"type": "string"},
                                                "mcp": {"type": "string"},
                                                "tool": {"type": "string"},
                                                "params": {"type": "object"}
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "required": ["workflow_name"]
                    }
                ),
                Tool(
                    name="create_workflow",
                    description="Create a custom workflow",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "Unique workflow ID"
                            },
                            "workflow_name": {
                                "type": "string",
                                "description": "Workflow name"
                            },
                            "description": {
                                "type": "string",
                                "description": "Workflow description"
                            },
                            "steps": {
                                "type": "array",
                                "description": "Workflow steps",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "step": {"type": "string"},
                                        "mcp": {"type": "string"},
                                        "tool": {"type": "string"},
                                        "params": {"type": "object"},
                                        "condition": {
                                            "type": "string",
                                            "description": "Optional condition for executing this step"
                                        }
                                    }
                                }
                            }
                        },
                        "required": ["workflow_id", "workflow_name", "steps"]
                    }
                ),
                Tool(
                    name="list_workflows",
                    description="List all available workflows",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Filter by type (predefined/custom/all)",
                                "enum": ["predefined", "custom", "all"],
                                "default": "all"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_workflow_status",
                    description="Get status of a running workflow",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "Workflow ID or execution ID"
                            }
                        },
                        "required": ["workflow_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
            """处理工具调用"""
            try:
                if name == "execute_workflow":
                    result = await self._execute_workflow(
                        arguments.get("workflow_name"),
                        arguments.get("params", {})
                    )
                elif name == "create_workflow":
                    result = await self._create_workflow(
                        arguments.get("workflow_id"),
                        arguments.get("workflow_name"),
                        arguments.get("description", ""),
                        arguments.get("steps", [])
                    )
                elif name == "list_workflows":
                    result = await self._list_workflows(arguments.get("type", "all"))
                elif name == "get_workflow_status":
                    result = await self._get_workflow_status(arguments.get("workflow_id"))
                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(type="text", text=json.dumps({
                    "error": str(e),
                    "tool": name
                }, ensure_ascii=False, indent=2))]

    def _load_workflows(self):
        """加载工作流配置"""
        # 预定义工作流
        self.workflows = {
            "publish": {
                "workflow_id": "publish",
                "workflow_name": "一键发布",
                "description": "自动生成内容并发布",
                "steps": [
                    {
                        "step": "generate_content",
                        "mcp": "llm",  # 使用内置 LLM
                        "tool": "generate",
                        "description": "生成标题、正文、标签"
                    },
                    {
                        "step": "generate_image",
                        "mcp": "stability-mcp",
                        "tool": "generate_image",
                        "description": "生成配图"
                    },
                    {
                        "step": "publish",
                        "mcp": "xiaohongshu-mcp",
                        "tool": "publish_note",
                        "description": "发布笔记"
                    },
                    {
                        "step": "log_result",
                        "mcp": "integration-mcp",
                        "tool": "log",
                        "description": "记录结果"
                    }
                ]
            },
            "create": {
                "workflow_id": "create",
                "workflow_name": "AI 创作增强",
                "description": "基于搜索和数据分析生成高质量内容",
                "steps": [
                    {
                        "step": "search_content",
                        "mcp": "tavily-remote",
                        "tool": "search",
                        "description": "搜索相关资料"
                    },
                    {
                        "step": "analyze_trends",
                        "mcp": "xiaohongshu-mcp",
                        "tool": "search_notes",
                        "description": "分析热门内容"
                    },
                    {
                        "step": "generate_content",
                        "mcp": "llm",
                        "tool": "generate",
                        "description": "基于搜索结果生成内容"
                    },
                    {
                        "step": "generate_image",
                        "mcp": "stability-mcp",
                        "tool": "generate_image",
                        "description": "生成风格化配图"
                    },
                    {
                        "step": "preview",
                        "mcp": "integration-mcp",
                        "tool": "preview",
                        "description": "展示预览"
                    },
                    {
                        "step": "publish",
                        "mcp": "xiaohongshu-mcp",
                        "tool": "publish_note",
                        "description": "用户确认后发布",
                        "condition": "user_confirmed"
                    }
                ]
            },
            "analyze": {
                "workflow_id": "analyze",
                "workflow_name": "数据分析",
                "description": "分析笔记表现并生成优化建议",
                "steps": [
                    {
                        "step": "fetch_data",
                        "mcp": "xiaohongshu-mcp",
                        "tool": "get_creator_info",
                        "description": "获取创作者数据"
                    },
                    {
                        "step": "analyze_metrics",
                        "mcp": "analytics-mcp",
                        "tool": "analyze_engagement",
                        "description": "分析互动数据"
                    },
                    {
                        "step": "generate_report",
                        "mcp": "analytics-mcp",
                        "tool": "generate_report",
                        "description": "生成分析报告"
                    },
                    {
                        "step": "get_recommendations",
                        "mcp": "analytics-mcp",
                        "tool": "get_recommendations",
                        "description": "生成优化建议"
                    }
                ]
            },
            "batch": {
                "workflow_id": "batch",
                "workflow_name": "批量操作",
                "description": "批量生成和发布内容",
                "steps": [
                    {
                        "step": "create_queue",
                        "mcp": "integration-mcp",
                        "tool": "create_queue",
                        "description": "创建任务队列"
                    },
                    {
                        "step": "parallel_generation",
                        "mcp": "llm",
                        "tool": "generate_batch",
                        "description": "并发生成内容",
                        "params": {
                            "max_concurrent": 3
                        }
                    },
                    {
                        "step": "quality_check",
                        "mcp": "integration-mcp",
                        "tool": "quality_check",
                        "description": "质量检查"
                    },
                    {
                        "step": "scheduled_publish",
                        "mcp": "scheduler-mcp",
                        "tool": "add_job",
                        "description": "分时发布",
                        "params": {
                            "interval_minutes": 30
                        }
                    }
                ]
            }
        }

        # 加载自定义工作流
        if WORKFLOWS_FILE.exists():
            try:
                with open(WORKFLOWS_FILE, 'r', encoding='utf-8') as f:
                    custom_workflows = json.load(f)
                    self.workflows.update(custom_workflows)
                logger.info(f"Loaded {len(custom_workflows)} custom workflows")
            except Exception as e:
                logger.error(f"Error loading custom workflows: {e}")

        logger.info(f"Total workflows loaded: {len(self.workflows)}")

    def _get_status(self) -> Dict[str, Any]:
        """获取集成状态"""
        return {
            "status": "running",
            "workflows_loaded": len(self.workflows),
            "available_mcps": [
                "xiaohongshu-mcp",
                "stability-mcp",
                "tavily-remote",
                "scheduler-mcp",
                "analytics-mcp",
                "integration-mcp"
            ],
            "timestamp": datetime.now().isoformat()
        }

    async def _execute_workflow(self, workflow_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流"""
        logger.info(f"Executing workflow: {workflow_name}")

        if workflow_name not in self.workflows:
            # 尝试执行自定义工作流
            if workflow_name == "custom":
                return await self._execute_custom_workflow(params.get("custom_steps", []))
            else:
                return {"error": f"Unknown workflow: {workflow_name}"}

        workflow = self.workflows[workflow_name]
        steps = workflow.get("steps", [])

        execution_id = f"{workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = []

        for i, step in enumerate(steps):
            step_name = step.get("step")
            mcp = step.get("mcp")
            tool = step.get("tool")
            step_params = step.get("params", {})
            condition = step.get("condition")

            # 检查条件
            if condition and not self._check_condition(condition, params):
                logger.info(f"Skipping step {step_name} due to condition")
                continue

            logger.info(f"Executing step {i+1}/{len(steps)}: {step_name}")

            try:
                # 执行步骤
                step_result = await self._execute_step(mcp, tool, {**step_params, **params})
                results.append({
                    "step": step_name,
                    "status": "success",
                    "result": step_result
                })

                # 将结果传递给下一步
                if isinstance(step_result, dict):
                    params.update(step_result)

            except Exception as e:
                logger.error(f"Error executing step {step_name}: {e}")
                results.append({
                    "step": step_name,
                    "status": "error",
                    "error": str(e)
                })
                # 决定是否继续
                if workflow_name in ["publish", "create"]:
                    # 发布和创作工作流在错误时停止
                    break

        return {
            "success": True,
            "workflow": workflow_name,
            "execution_id": execution_id,
            "steps_completed": len([r for r in results if r["status"] == "success"]),
            "steps_total": len(steps),
            "results": results
        }

    async def _execute_custom_workflow(self, custom_steps: List[Dict]) -> Dict[str, Any]:
        """执行自定义工作流"""
        execution_id = f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = []

        for i, step in enumerate(custom_steps):
            step_name = step.get("step")
            mcp = step.get("mcp")
            tool = step.get("tool")
            params = step.get("params", {})

            logger.info(f"Executing custom step {i+1}/{len(custom_steps)}: {step_name}")

            try:
                step_result = await self._execute_step(mcp, tool, params)
                results.append({
                    "step": step_name,
                    "status": "success",
                    "result": step_result
                })
            except Exception as e:
                logger.error(f"Error executing step {step_name}: {e}")
                results.append({
                    "step": step_name,
                    "status": "error",
                    "error": str(e)
                })

        return {
            "success": True,
            "workflow": "custom",
            "execution_id": execution_id,
            "results": results
        }

    async def _execute_step(self, mcp: str, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个步骤

        注意：这是框架代码，实际调用需要通过 MCP 客户端
        这里返回模拟结果，实际实现需要集成 MCP 客户端
        """
        logger.info(f"Calling {mcp}.{tool} with params: {params}")

        # 这里应该是实际的 MCP 调用
        # 目前返回模拟结果
        if mcp == "llm" and tool == "generate":
            return {
                "title": f"AI生成标题: {params.get('topic', '')}",
                "body": f"这是关于{params.get('topic', '')}的内容...",
                "tags": ["#标签1", "#标签2", "#标签3"]
            }
        elif mcp == "stability-mcp" and tool == "generate_image":
            return {
                "image_url": f"https://example.com/image_{datetime.now().timestamp()}.png"
            }
        elif mcp == "xiaohongshu-mcp" and tool == "publish_note":
            return {
                "post_id": f"xhs_{datetime.now().timestamp()}",
                "post_url": "https://xiaohongshu.com/x/example"
            }
        else:
            return {
                "mcp": mcp,
                "tool": tool,
                "params": params,
                "executed": True
            }

    def _check_condition(self, condition: str, params: Dict[str, Any]) -> bool:
        """检查条件是否满足"""
        if condition == "user_confirmed":
            return params.get("user_confirmed", False)
        # 其他条件...
        return True

    async def _create_workflow(self, workflow_id: str, workflow_name: str,
                               description: str, steps: List[Dict]) -> Dict[str, Any]:
        """创建自定义工作流"""
        if workflow_id in self.workflows:
            return {"error": f"Workflow ID {workflow_id} already exists"}

        workflow = {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "description": description,
            "steps": steps,
            "created_at": datetime.now().isoformat()
        }

        self.workflows[workflow_id] = workflow

        # 保存到文件
        WORKFLOWS_FILE.parent.mkdir(parents=True, exist_ok=True)
        custom_workflows = {k: v for k, v in self.workflows.items() if k not in ["publish", "create", "analyze", "batch"]}

        try:
            with open(WORKFLOWS_FILE, 'w', encoding='utf-8') as f:
                json.dump(custom_workflows, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving workflow: {e}")

        logger.info(f"Created workflow: {workflow_id}")

        return {
            "success": True,
            "message": f"Workflow {workflow_id} created successfully",
            "workflow": workflow
        }

    async def _list_workflows(self, workflow_type: str = "all") -> Dict[str, Any]:
        """列出工作流"""
        workflows = []

        for workflow_id, workflow in self.workflows.items():
            is_predefined = workflow_id in ["publish", "create", "analyze", "batch"]

            if workflow_type == "all":
                workflows.append(workflow)
            elif workflow_type == "predefined" and is_predefined:
                workflows.append(workflow)
            elif workflow_type == "custom" and not is_predefined:
                workflows.append(workflow)

        return {
            "success": True,
            "count": len(workflows),
            "workflows": workflows
        }

    async def _get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """获取工作流状态"""
        if workflow_id in self.workflows:
            return {
                "success": True,
                "workflow": self.workflows[workflow_id],
                "status": "available"
            }
        else:
            return {
                "success": False,
                "error": f"Workflow {workflow_id} not found"
            }

    async def run(self):
        """启动服务器"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="integration-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )


async def main():
    """主函数"""
    integration_mcp = IntegrationMCP()
    await integration_mcp.run()


if __name__ == "__main__":
    asyncio.run(main())
