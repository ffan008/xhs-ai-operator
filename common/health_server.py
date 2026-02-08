"""
健康检查 HTTP 服务器

提供 /health、/health/live、/health/ready 等端点。
"""

import asyncio
import json
from datetime import datetime
from typing import Optional
from aiohttp import web, WSMsgType
from aiohttp.web import Application, Request, Response, WebSocketResponse
import logging

from .health_check import (
    HealthChecker,
    CheckResult,
    HealthStatus,
    default_health_checker
)


# ============================================================================
# 日志配置
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 健康检查 HTTP 服务器
# ============================================================================

class HealthCheckServer:
    """健康检查 HTTP 服务器"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        health_checker: Optional[HealthChecker] = None
    ):
        """
        初始化服务器

        Args:
            host: 监听地址
            port: 监听端口
            health_checker: 健康检查器
        """
        self.host = host
        self.port = port
        self.health_checker = health_checker or default_health_checker
        self.app: Optional[Application] = None
        self.runner = None
        self.site = None
        self._websocket_clients = set()

    def create_app(self) -> Application:
        """创建应用"""
        app = web.Application()
        app.router.add_get("/health", self.health_handler)
        app.router.add_get("/health/live", self.liveness_handler)
        app.router.add_get("/health/ready", self.readiness_handler)
        app.router.add_get("/health/{check_name}", self.specific_check_handler)
        app.router.add_get("/health/stats", self.stats_handler)
        app.router.add_get("/health/history", self.history_handler)
        app.router.add_get("/health/ws", self.websocket_handler)

        # 健康检查
        app.router.add_get("/", self.root_handler)

        return app

    async def root_handler(self, request: Request) -> Response:
        """根路径处理"""
        return web.json_response({
            "service": self.health_checker.service_name,
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "health": "/health",
                "liveness": "/health/live",
                "readiness": "/health/ready",
                "specific_check": "/health/{check_name}",
                "stats": "/health/stats",
                "history": "/health/history",
                "websocket": "/health/ws"
            }
        })

    async def health_handler(self, request: Request) -> Response:
        """
        健康检查端点

        GET /health
        """
        try:
            result = await self.health_checker.check_health()

            # 根据 HTTP 状态码返回
            status_code = 200
            if result["status"] == HealthStatus.UNHEALTHY.value:
                status_code = 503
            elif result["status"] == HealthStatus.DEGRADED.value:
                status_code = 200  # 降级仍返回 200

            return web.json_response(result, status=status_code)

        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return web.json_response({
                "service": self.health_checker.service_name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)

    async def liveness_handler(self, request: Request) -> Response:
        """
        存活检查端点

        GET /health/live
        """
        try:
            result = await self.health_checker.check_liveness()
            return web.json_response(result, status=200)
        except Exception as e:
            logger.error(f"存活检查失败: {e}")
            return web.json_response({
                "service": self.health_checker.service_name,
                "status": "dead",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=503)

    async def readiness_handler(self, request: Request) -> Response:
        """
        就绪检查端点

        GET /health/ready
        """
        try:
            result = await self.health_checker.check_readiness()

            # 就绪返回 200，未就绪返回 503
            status_code = 200 if result["status"] == "ready" else 503
            return web.json_response(result, status=status_code)

        except Exception as e:
            logger.error(f"就绪检查失败: {e}")
            return web.json_response({
                "service": self.health_checker.service_name,
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=503)

    async def specific_check_handler(self, request: Request) -> Response:
        """
        特定检查项端点

        GET /health/{check_name}
        """
        check_name = request.match_info.get("check_name")

        try:
            result = await self.health_checker.check_health(check_name)

            # 根据 HTTP 状态码返回
            status_code = 200
            if "check" in result:
                check_status = result["check"]["status"]
                if check_status == HealthStatus.UNHEALTHY.value:
                    status_code = 503
                elif check_status == HealthStatus.UNKNOWN.value:
                    status_code = 503
            elif "error" in result:
                status_code = 404

            return web.json_response(result, status=status_code)

        except Exception as e:
            logger.error(f"检查 {check_name} 失败: {e}")
            return web.json_response({
                "service": self.health_checker.service_name,
                "check": check_name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)

    async def stats_handler(self, request: Request) -> Response:
        """
        统计信息端点

        GET /health/stats
        """
        try:
            stats = self.health_checker.get_stats()
            return web.json_response(stats, status=200)
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return web.json_response({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)

    async def history_handler(self, request: Request) -> Response:
        """
        历史记录端点

        GET /health/history?limit=10
        """
        try:
            limit = int(request.query.get("limit", "10"))
            history = self.health_checker.get_check_history(limit)
            return web.json_response({
                "history": history,
                "count": len(history)
            }, status=200)
        except Exception as e:
            logger.error(f"获取历史失败: {e}")
            return web.json_response({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)

    async def websocket_handler(self, request: Request) -> WebSocketResponse:
        """
        WebSocket 端点 - 实时健康检查推送

        WS /health/ws
        """
        ws = WebSocketResponse()
        await ws.prepare(request)

        self._websocket_clients.add(ws)
        logger.info(f"WebSocket 客户端连接: {request.remote}")

        try:
            # 发送欢迎消息
            await ws.send_json({
                "type": "connected",
                "message": "已连接到健康检查服务",
                "timestamp": datetime.now().isoformat()
            })

            # 保持连接并定期发送健康状态
            while True:
                try:
                    # 等待客户端消息（心跳）
                    msg = await asyncio.wait_for(ws.receive(), timeout=30.0)

                    if msg.type == WSMsgType.TEXT:
                        data = json.loads(msg.data)

                        # 处理请求
                        if data.get("action") == "check":
                            result = await self.health_checker.check_health()
                            await ws.send_json({
                                "type": "health_check",
                                "data": result
                            })

                    elif msg.type == WSMsgType.ERROR:
                        logger.error(f"WebSocket 错误: {ws.exception()}")
                        break

                except asyncio.TimeoutError:
                    # 发送心跳
                    await ws.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat()
                    })

        except Exception as e:
            logger.error(f"WebSocket 错误: {e}")

        finally:
            self._websocket_clients.discard(ws)
            logger.info(f"WebSocket 客户端断开: {request.remote}")

        return ws

    async def broadcast_health(self) -> None:
        """向所有 WebSocket 客户端广播健康状态"""
        if not self._websocket_clients:
            return

        result = await self.health_checker.check_health()

        for ws in list(self._websocket_clients):
            try:
                await ws.send_json({
                    "type": "health_update",
                    "data": result
                })
            except Exception as e:
                logger.error(f"广播失败: {e}")
                self._websocket_clients.discard(ws)

    async def start(self) -> None:
        """启动服务器"""
        self.app = self.create_app()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        logger.info(f"健康检查服务器启动: http://{self.host}:{self.port}")
        logger.info(f"端点:")
        logger.info(f"  - GET /health")
        logger.info(f"  - GET /health/live")
        logger.info(f"  - GET /health/ready")
        logger.info(f"  - GET /health/{{check_name}}")
        logger.info(f"  - GET /health/stats")
        logger.info(f"  - GET /health/history")
        logger.info(f"  - WS  /health/ws")

    async def stop(self) -> None:
        """停止服务器"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

        # 关闭所有 WebSocket 连接
        for ws in list(self._websocket_clients):
            await ws.close()

        logger.info("健康检查服务器已停止")

    async def run_forever(self) -> None:
        """持续运行服务器"""
        await self.start()

        try:
            while True:
                await asyncio.sleep(3600)  # 每小时广播一次健康状态
                await self.broadcast_health()

        except asyncio.CancelledError:
            await self.stop()


# ============================================================================
# 便捷函数
# ============================================================================

async def start_health_server(
    host: str = "0.0.0.0",
    port: int = 8080
) -> HealthCheckServer:
    """
    启动健康检查服务器

    Args:
        host: 监听地址
        port: 监听端口

    Returns:
        服务器实例
    """
    server = HealthCheckServer(host, port)
    await server.start()
    return server


if __name__ == "__main__":
    # 运行服务器
    server = HealthCheckServer()

    try:
        asyncio.run(server.run_forever())
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        asyncio.run(server.stop())
        print("服务器已停止")
