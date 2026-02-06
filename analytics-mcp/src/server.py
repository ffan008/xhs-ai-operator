#!/usr/bin/env python3
"""
小红书 AI 运营系统 - Analytics MCP Server
数据分析和报告生成服务器
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path
from collections import defaultdict

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
logger = logging.getLogger("analytics-mcp")

# 数据存储路径
DATA_DIR = Path(__file__).parent.parent / "data"
ANALYTICS_FILE = DATA_DIR / "analytics.json"


class AnalyticsMCP:
    """Analytics MCP 服务器"""

    def __init__(self):
        self.server = Server("analytics-mcp")
        self.analytics_data = {}
        self._setup_handlers()

        # 确保数据目录存在
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 加载历史数据
        self._load_data()

    def _setup_handlers(self):
        """设置 MCP 处理器"""

        @self.server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            """列出可用资源"""
            return [
                Resource(
                    uri="analytics://reports",
                    name="Analytics Reports",
                    description="Historical analytics reports",
                    mimeType="application/json"
                ),
                Resource(
                    uri="analytics://insights",
                    name="Content Insights",
                    description="Content performance insights",
                    mimeType="application/json"
                )
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """读取资源"""
            if uri == "analytics://reports":
                return json.dumps(self.analytics_data, ensure_ascii=False, indent=2)
            elif uri == "analytics://insights":
                return json.dumps(self._generate_insights(), ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """列出可用工具"""
            return [
                Tool(
                    name="analyze_engagement",
                    description="Analyze engagement metrics for posts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "posts": {
                                "type": "array",
                                "description": "List of posts with engagement data",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "post_id": {"type": "string"},
                                        "title": {"type": "string"},
                                        "views": {"type": "number"},
                                        "likes": {"type": "number"},
                                        "comments": {"type": "number"},
                                        "shares": {"type": "number"},
                                        "saves": {"type": "number"},
                                        "publish_time": {"type": "string"}
                                    }
                                }
                            },
                            "time_range": {
                                "type": "object",
                                "description": "Time range for analysis",
                                "properties": {
                                    "start_date": {"type": "string"},
                                    "end_date": {"type": "string"}
                                }
                            }
                        },
                        "required": ["posts"]
                    }
                ),
                Tool(
                    name="generate_report",
                    description="Generate comprehensive analytics report",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_data": {
                                "type": "object",
                                "description": "Account information and post data",
                                "properties": {
                                    "account_info": {
                                        "type": "object",
                                        "properties": {
                                            "account_id": {"type": "string"},
                                            "nickname": {"type": "string"},
                                            "fans_count": {"type": "number"}
                                        }
                                    },
                                    "posts": {
                                        "type": "array",
                                        "items": {"type": "object"}
                                    }
                                }
                            },
                            "report_type": {
                                "type": "string",
                                "description": "Type of report",
                                "enum": ["overview", "detailed", "trends", "comparison"],
                                "default": "detailed"
                            },
                            "format": {
                                "type": "string",
                                "description": "Output format",
                                "enum": ["markdown", "json", "html"],
                                "default": "markdown"
                            }
                        },
                        "required": ["account_data"]
                    }
                ),
                Tool(
                    name="analyze_content_performance",
                    description="Analyze performance by content type",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "posts": {
                                "type": "array",
                                "description": "List of posts with metadata",
                                "items": {"type": "object"}
                            },
                            "categorize_by": {
                                "type": "string",
                                "description": "How to categorize content",
                                "enum": ["tags", "style", "topic", "custom"],
                                "default": "tags"
                            }
                        },
                        "required": ["posts"]
                    }
                ),
                Tool(
                    name="analyze_time_patterns",
                    description="Analyze posting time patterns and best times",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "posts": {
                                "type": "array",
                                "description": "List of posts with timestamps and performance",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "publish_time": {"type": "string"},
                                        "views": {"type": "number"},
                                        "engagement_rate": {"type": "number"}
                                    }
                                }
                            }
                        },
                        "required": ["posts"]
                    }
                ),
                Tool(
                    name="compare_periods",
                    description="Compare performance between two time periods",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "period1": {
                                "type": "object",
                                "properties": {
                                    "posts": {"type": "array"},
                                    "label": {"type": "string"}
                                }
                            },
                            "period2": {
                                "type": "object",
                                "properties": {
                                    "posts": {"type": "array"},
                                    "label": {"type": "string"}
                                }
                            }
                        },
                        "required": ["period1", "period2"]
                    }
                ),
                Tool(
                    name="get_recommendations",
                    description="Get AI-powered recommendations based on analysis",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "analysis_result": {
                                "type": "object",
                                "description": "Analysis result from other tools"
                            },
                            "focus_areas": {
                                "type": "array",
                                "description": "Areas to focus on",
                                "items": {
                                    "type": "string",
                                    "enum": ["content", "timing", "engagement", "growth", "all"]
                                },
                                "default": ["all"]
                            }
                        },
                        "required": ["analysis_result"]
                    }
                ),
                Tool(
                    name="export_data",
                    description="Export analytics data in various formats",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "object",
                                "description": "Data to export"
                            },
                            "format": {
                                "type": "string",
                                "enum": ["csv", "json", "excel"],
                                "default": "json"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Output filename (without extension)"
                            }
                        },
                        "required": ["data", "format"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
            """处理工具调用"""
            try:
                if name == "analyze_engagement":
                    result = await self._analyze_engagement(
                        arguments.get("posts", []),
                        arguments.get("time_range")
                    )
                elif name == "generate_report":
                    result = await self._generate_report(
                        arguments.get("account_data"),
                        arguments.get("report_type", "detailed"),
                        arguments.get("format", "markdown")
                    )
                elif name == "analyze_content_performance":
                    result = await self._analyze_content_performance(
                        arguments.get("posts", []),
                        arguments.get("categorize_by", "tags")
                    )
                elif name == "analyze_time_patterns":
                    result = await self._analyze_time_patterns(arguments.get("posts", []))
                elif name == "compare_periods":
                    result = await self._compare_periods(
                        arguments.get("period1", {}),
                        arguments.get("period2", {})
                    )
                elif name == "get_recommendations":
                    result = await self._get_recommendations(
                        arguments.get("analysis_result", {}),
                        arguments.get("focus_areas", ["all"])
                    )
                elif name == "export_data":
                    result = await self._export_data(
                        arguments.get("data", {}),
                        arguments.get("format", "json"),
                        arguments.get("filename", f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                    )
                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(type="text", text=json.dumps({
                    "error": str(e),
                    "tool": name
                }, ensure_ascii=False, indent=2))]

    def _load_data(self):
        """加载历史数据"""
        if ANALYTICS_FILE.exists():
            try:
                with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                    self.analytics_data = json.load(f)
                logger.info("Loaded analytics data")
            except Exception as e:
                logger.error(f"Error loading analytics data: {e}")

    def _save_data(self):
        """保存数据"""
        try:
            with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.analytics_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving analytics data: {e}")

    def _generate_insights(self) -> Dict[str, Any]:
        """生成内容洞察"""
        # 这里基于历史数据生成洞察
        return {
            "generated_at": datetime.now().isoformat(),
            "insights": []
        }

    async def _analyze_engagement(self, posts: List[Dict], time_range: Optional[Dict] = None) -> Dict[str, Any]:
        """分析互动数据"""
        if not posts:
            return {"error": "No posts provided"}

        total_views = sum(p.get("views", 0) for p in posts)
        total_likes = sum(p.get("likes", 0) for p in posts)
        total_comments = sum(p.get("comments", 0) for p in posts)
        total_shares = sum(p.get("shares", 0) for p in posts)
        total_saves = sum(p.get("saves", 0) for p in posts)
        total_engagement = total_likes + total_comments + total_shares + total_saves

        avg_engagement_rate = (total_engagement / total_views * 100) if total_views > 0 else 0

        # 计算互动构成
        engagement_breakdown = {
            "likes": {
                "total": total_likes,
                "percentage": (total_likes / total_engagement * 100) if total_engagement > 0 else 0
            },
            "comments": {
                "total": total_comments,
                "percentage": (total_comments / total_engagement * 100) if total_engagement > 0 else 0
            },
            "shares": {
                "total": total_shares,
                "percentage": (total_shares / total_engagement * 100) if total_engagement > 0 else 0
            },
            "saves": {
                "total": total_saves,
                "percentage": (total_saves / total_engagement * 100) if total_engagement > 0 else 0
            }
        }

        # 找出表现最佳的内容
        sorted_by_views = sorted(posts, key=lambda x: x.get("views", 0), reverse=True)
        sorted_by_engagement = sorted(posts, key=lambda x: (
            x.get("likes", 0) + x.get("comments", 0) + x.get("shares", 0) + x.get("saves", 0)
        ), reverse=True)

        return {
            "success": True,
            "summary": {
                "total_views": total_views,
                "total_engagement": total_engagement,
                "avg_engagement_rate": round(avg_engagement_rate, 2),
                "posts_analyzed": len(posts)
            },
            "engagement_breakdown": engagement_breakdown,
            "top_performing": {
                "by_views": sorted_by_views[:5],
                "by_engagement": sorted_by_engagement[:5]
            }
        }

    async def _generate_report(self, account_data: Dict, report_type: str, format_type: str) -> Dict[str, Any]:
        """生成分析报告"""
        account_info = account_data.get("account_info", {})
        posts = account_data.get("posts", [])

        if not posts:
            return {"error": "No posts to analyze"}

        # 基础分析
        engagement_analysis = await self._analyze_engagement(posts)
        content_analysis = await self._analyze_content_performance(posts, "tags")
        time_analysis = await self._analyze_time_patterns(posts)

        # 生成报告
        if format_type == "markdown":
            report = self._format_markdown_report(
                account_info,
                engagement_analysis,
                content_analysis,
                time_analysis
            )
        elif format_type == "json":
            report = {
                "account_info": account_info,
                "engagement_analysis": engagement_analysis,
                "content_analysis": content_analysis,
                "time_analysis": time_analysis,
                "generated_at": datetime.now().isoformat()
            }
        else:  # html
            report = self._format_html_report(
                account_info,
                engagement_analysis,
                content_analysis,
                time_analysis
            )

        # 保存到历史
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.analytics_data[report_id] = {
            "type": report_type,
            "generated_at": datetime.now().isoformat(),
            "data": account_data
        }
        self._save_data()

        return {
            "success": True,
            "report_id": report_id,
            "format": format_type,
            "content": report
        }

    def _format_markdown_report(self, account_info: Dict, engagement: Dict,
                                 content: Dict, time_analysis: Dict) -> str:
        """格式化为 Markdown 报告"""
        md = f"""# 📊 小红书数据分析报告

**账号名称**: {account_info.get('nickname', 'N/A')}
**粉丝数量**: {account_info.get('fans_count', 0):,}
**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📈 一、整体表现

### 核心数据概览

| 指标 | 数值 |
|------|------|
| 分析笔记数 | {engagement['summary']['posts_analyzed']} |
| 总浏览量 | {engagement['summary']['total_views']:,} |
| 总互动量 | {engagement['summary']['total_engagement']:,} |
| 平均互动率 | {engagement['summary']['avg_engagement_rate']}% |

### 互动构成

```
点赞：{engagement['engagement_breakdown']['likes']['percentage']:.1f}% ▓▓▓▓▓▓▓▓▓▓▓▓▓▓
评论：{engagement['engagement_breakdown']['comments']['percentage']:.1f}% ▓▓▓▓
收藏：{engagement['engagement_breakdown']['saves']['percentage']:.1f}% ▓▓▓▓▓▓
分享：{engagement['engagement_breakdown']['shares']['percentage']:.1f}% ▓▓
```

---

## 🏆 二、最佳表现内容

### Top 5 高浏览笔记
"""
        for i, post in enumerate(engagement['top_performing']['by_views'][:5], 1):
            md += f"""
{i}. **{post.get('title', 'N/A')}**
   - 👀 浏览量：{post.get('views', 0):,}
   - ❤️ 互动：{post.get('likes', 0)} 赞 | {post.get('comments', 0)} 评 | {post.get('saves', 0)} 藏
"""

        md += "\n---\n\n**报告由 AI 小红书运营助手生成**"

        return md

    def _format_html_report(self, account_info: Dict, engagement: Dict,
                            content: Dict, time_analysis: Dict) -> str:
        """格式化为 HTML 报告"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>小红书数据分析报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; }}
        h1 {{ color: #ff2442; }}
        h2 {{ color: #333; border-bottom: 2px solid #ff2442; padding-bottom: 10px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #ff2442; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .metric {{ display: inline-block; margin: 20px; padding: 20px; background: #f5f5f5; border-radius: 8px; }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #ff2442; }}
        .metric-label {{ font-size: 14px; color: #666; }}
    </style>
</head>
<body>
    <h1>📊 小红书数据分析报告</h1>
    <p><strong>账号名称</strong>: {account_info.get('nickname', 'N/A')}</p>
    <p><strong>报告生成时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>📈 核心指标</h2>
    <div class="metric">
        <div class="metric-value">{engagement['summary']['posts_analyzed']}</div>
        <div class="metric-label">分析笔记数</div>
    </div>
    <div class="metric">
        <div class="metric-value">{engagement['summary']['total_views']:,}</div>
        <div class="metric-label">总浏览量</div>
    </div>
    <div class="metric">
        <div class="metric-value">{engagement['summary']['avg_engagement_rate']}%</div>
        <div class="metric-label">平均互动率</div>
    </div>

    <h2>🏆 最佳表现内容</h2>
    <table>
        <tr>
            <th>排名</th>
            <th>标题</th>
            <th>浏览量</th>
            <th>互动量</th>
        </tr>
"""
        for i, post in enumerate(engagement['top_performing']['by_views'][:5], 1):
            html += f"""
        <tr>
            <td>{i}</td>
            <td>{post.get('title', 'N/A')}</td>
            <td>{post.get('views', 0):,}</td>
            <td>{post.get('likes', 0) + post.get('comments', 0) + post.get('saves', 0):,}</td>
        </tr>"""

        html += """
    </table>

    <p><em>报告由 AI 小红书运营助手生成</em></p>
</body>
</html>"""
        return html

    async def _analyze_content_performance(self, posts: List[Dict], categorize_by: str) -> Dict[str, Any]:
        """分析内容表现"""
        categories = defaultdict(lambda: {"count": 0, "total_views": 0, "total_engagement": 0})

        for post in posts:
            if categorize_by == "tags":
                tags = post.get("tags", [])
                for tag in tags:
                    categories[tag]["count"] += 1
                    categories[tag]["total_views"] += post.get("views", 0)
                    categories[tag]["total_engagement"] += (
                        post.get("likes", 0) + post.get("comments", 0) +
                        post.get("shares", 0) + post.get("saves", 0)
                    )
            else:
                # 其他分类方式
                pass

        # 计算平均值
        for cat, data in categories.items():
            if data["count"] > 0:
                data["avg_views"] = data["total_views"] / data["count"]
                data["avg_engagement"] = data["total_engagement"] / data["count"]
                data["avg_engagement_rate"] = (
                    (data["total_engagement"] / data["total_views"] * 100)
                    if data["total_views"] > 0 else 0
                )

        # 排序
        sorted_categories = sorted(
            categories.items(),
            key=lambda x: x[1]["avg_engagement_rate"],
            reverse=True
        )

        return {
            "success": True,
            "categorize_by": categorize_by,
            "categories": dict(sorted_categories)
        }

    async def _analyze_time_patterns(self, posts: List[Dict]) -> Dict[str, Any]:
        """分析时间规律"""
        hourly_stats = defaultdict(lambda: {"posts": 0, "total_views": 0, "total_engagement": 0})
        weekday_stats = defaultdict(lambda: {"posts": 0, "total_views": 0, "total_engagement": 0})

        for post in posts:
            try:
                publish_time = datetime.fromisoformat(post.get("publish_time", ""))
                hour = publish_time.hour
                weekday = publish_time.weekday()

                hourly_stats[hour]["posts"] += 1
                hourly_stats[hour]["total_views"] += post.get("views", 0)
                hourly_stats[hour]["total_engagement"] += (
                    post.get("likes", 0) + post.get("comments", 0) +
                    post.get("shares", 0) + post.get("saves", 0)
                )

                weekday_stats[weekday]["posts"] += 1
                weekday_stats[weekday]["total_views"] += post.get("views", 0)
                weekday_stats[weekday]["total_engagement"] += (
                    post.get("likes", 0) + post.get("comments", 0) +
                    post.get("shares", 0) + post.get("saves", 0)
                )
            except Exception as e:
                logger.warning(f"Error parsing publish time: {e}")
                continue

        # 计算平均值
        for hour, data in hourly_stats.items():
            if data["posts"] > 0:
                data["avg_engagement_rate"] = (
                    (data["total_engagement"] / data["total_views"] * 100)
                    if data["total_views"] > 0 else 0
                )

        for weekday, data in weekday_stats.items():
            if data["posts"] > 0:
                data["avg_engagement_rate"] = (
                    (data["total_engagement"] / data["total_views"] * 100)
                    if data["total_views"] > 0 else 0
                )

        # 找出最佳时段
        best_hours = sorted(
            hourly_stats.items(),
            key=lambda x: x[1]["avg_engagement_rate"],
            reverse=True
        )[:5]

        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        best_weekdays = sorted(
            weekday_stats.items(),
            key=lambda x: x[1]["avg_engagement_rate"],
            reverse=True
        )[:3]

        return {
            "success": True,
            "best_hours": [{"hour": h, **data} for h, data in best_hours],
            "best_weekdays": [
                {"weekday": weekday_names[w], **data}
                for w, data in best_weekdays
            ]
        }

    async def _compare_periods(self, period1: Dict, period2: Dict) -> Dict[str, Any]:
        """对比两个时间段"""
        posts1 = period1.get("posts", [])
        posts2 = period2.get("posts", [])

        analysis1 = await self._analyze_engagement(posts1)
        analysis2 = await self._analyze_engagement(posts2)

        # 计算变化
        summary1 = analysis1.get("summary", {})
        summary2 = analysis2.get("summary", {})

        return {
            "success": True,
            "period1": {
                "label": period1.get("label", "Period 1"),
                "data": analysis1
            },
            "period2": {
                "label": period2.get("label", "Period 2"),
                "data": analysis2
            },
            "comparison": {
                "views_change": self._calculate_change(
                    summary1.get("total_views", 0),
                    summary2.get("total_views", 0)
                ),
                "engagement_change": self._calculate_change(
                    summary1.get("total_engagement", 0),
                    summary2.get("total_engagement", 0)
                ),
                "rate_change": self._calculate_change(
                    summary1.get("avg_engagement_rate", 0),
                    summary2.get("avg_engagement_rate", 0)
                )
            }
        }

    def _calculate_change(self, old_value: float, new_value: float) -> Dict[str, Any]:
        """计算变化"""
        if old_value == 0:
            change_percent = 100 if new_value > 0 else 0
        else:
            change_percent = ((new_value - old_value) / old_value) * 100

        return {
            "old": old_value,
            "new": new_value,
            "absolute_change": new_value - old_value,
            "percentage_change": round(change_percent, 2),
            "direction": "up" if change_percent > 0 else "down" if change_percent < 0 else "stable"
        }

    async def _get_recommendations(self, analysis_result: Dict, focus_areas: List[str]) -> Dict[str, Any]:
        """生成优化建议"""
        recommendations = {
            "content": [],
            "timing": [],
            "engagement": [],
            "growth": []
        }

        # 基于分析结果生成建议
        if "all" in focus_areas or "content" in focus_areas:
            recommendations["content"].extend([
                "✅ 持续创作高互动率的内容类型",
                "✅ 标题使用数字和emoji增强吸引力",
                "✅ 正文控制在600-800字，确保完读率"
            ])

        if "all" in focus_areas or "timing" in focus_areas:
            recommendations["timing"].extend([
                "✅ 在高互动时段发布内容",
                "✅ 保持每天1-2篇的发布频率",
                "✅ 避开深夜时段发布"
            ])

        if "all" in focus_areas or "engagement" in focus_areas:
            recommendations["engagement"].extend([
                "✅ 正文末尾增加互动引导",
                "✅ 及时回复用户评论",
                "✅ 收藏率高的内容可以做成系列"
            ])

        if "all" in focus_areas or "growth" in focus_areas:
            recommendations["growth"].extend([
                "✅ 保持账号垂直度",
                "✅ 参与平台话题和挑战",
                "✅ 与同领域账号互动"
            ])

        return {
            "success": True,
            "focus_areas": focus_areas,
            "recommendations": recommendations,
            "priority": ["high", "medium", "low"]
        }

    async def _export_data(self, data: Dict, format_type: str, filename: str) -> Dict[str, Any]:
        """导出数据"""
        output_path = DATA_DIR / f"{filename}.{format_type}"

        try:
            if format_type == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif format_type == "csv":
                # 简化的 CSV 导出
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    if isinstance(data, dict) and "posts" in data:
                        writer = csv.DictWriter(f, fieldnames=data["posts"][0].keys())
                        writer.writeheader()
                        writer.writerows(data["posts"])
            elif format_type == "excel":
                # Excel 导出需要 openpyxl
                return {"success": False, "error": "Excel export not implemented yet"}

            return {
                "success": True,
                "file": str(output_path),
                "format": format_type
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def run(self):
        """启动服务器"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="analytics-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )


async def main():
    """主函数"""
    analytics_mcp = AnalyticsMCP()
    await analytics_mcp.run()


if __name__ == "__main__":
    asyncio.run(main())
