"""
Prometheus HTTP Exporter

提供 HTTP 端点供 Prometheus 抓取指标。
"""

import asyncio
import time
from typing import Optional
from aiohttp import web, WSCMsgType
from aiohttp.web import Application, Request, Response
import logging

from .metrics import MetricRegistry, PerformanceCollector


# ============================================================================
# 日志配置
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Prometheus Exporter
# ============================================================================

class PrometheusExporter:
    """Prometheus HTTP Exporter"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9090,
        registry: Optional[MetricRegistry] = None,
        collector: Optional[PerformanceCollector] = None,
        collect_interval: float = 15.0
    ):
        """
        初始化 Exporter

        Args:
            host: 监听地址
            port: 监听端口
            registry: 指标注册表
            collector: 性能收集器
            collect_interval: 收集间隔（秒）
        """
        self.host = host
        self.port = port
        self.registry = registry
        self.collector = collector
        self.collect_interval = collect_interval

        self.app: Optional[Application] = None
        self.runner = None
        self.site = None

        # 自动收集任务
        self._auto_collect = True
        self._collect_task: Optional[asyncio.Task] = None

    def create_app(self) -> Application:
        """创建应用"""
        app = web.Application()

        # /metrics 端点
        app.router.add_get("/metrics", self.metrics_handler)

        / 健康检查
        app.router.add_get("/health", self.health_handler)

        # 根路径
        app.router.add_get("/", self.root_handler)

        return app

    async def root_handler(self, request: Request) -> Response:
        """根路径处理"""
        return web.json_response({
            "service": "prometheus-exporter",
            "version": "1.0.0",
            "endpoints": {
                "metrics": "/metrics",
                "health": "/health"
            }
        })

    async def metrics_handler(self, request: Request) -> Response:
        """
        指标端点

        GET /metrics
        """
        try:
            # 收集指标
            if self.collector:
                self.collector.collect()

            # 导出 Prometheus 格式
            if self.registry:
                metrics_text = self.registry.export_prometheus()
            else:
                metrics_text = "# No metrics registered"

            return web.Response(
                text=metrics_text,
                content_type="text/plain; version=0.0.4; charset=utf-8"
            )

        except Exception as e:
            logger.error(f"导出指标失败: {e}")
            return web.Response(
                text=f"# Error: {str(e)}",
                status=500,
                content_type="text/plain"
            )

    async def health_handler(self, request: Request) -> Response:
        """
        健康检查端点

        GET /health
        """
        return web.json_response({
            "status": "healthy",
            "timestamp": time.time()
        })

    async def start(self) -> None:
        """启动服务器"""
        self.app = self.create_app()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        logger.info(f"Prometheus Exporter 启动: http://{self.host}:{self.port}/metrics")

        # 启动自动收集
        if self.collector:
            self._collect_task = asyncio.create_task(self._auto_collect_loop())

    async def stop(self) -> None:
        """停止服务器"""
        self._auto_collect = False

        if self._collect_task:
            self._collect_task.cancel()
            try:
                await self._collect_task
            except asyncio.CancelledError:
                pass

        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

        logger.info("Prometheus Exporter 已停止")

    async def _auto_collect_loop(self) -> None:
        """自动收集循环"""
        while self._auto_collect:
            try:
                if self.collector:
                    self.collector.collect()
                await asyncio.sleep(self.collect_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自动收集失败: {e}")
                await asyncio.sleep(self.collect_interval)

    async def run_forever(self) -> None:
        """持续运行服务器"""
        await self.start()

        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            await self.stop()


# ============================================================================
# 便捷函数
# ============================================================================

async def start_exporter(
    host: str = "0.0.0.0",
    port: int = 9090,
    registry: Optional[MetricRegistry] = None,
    collector: Optional[PerformanceCollector] = None
) -> PrometheusExporter:
    """
    启动 Prometheus Exporter

    Args:
        host: 监听地址
        port: 监听端口
        registry: 指标注册表
        collector: 性能收集器

    Returns:
        Exporter 实例
    """
    exporter = PrometheusExporter(
        host=host,
        port=port,
        registry=registry,
        collector=collector
    )
    await exporter.start()
    return exporter


if __name__ == "__main__":
    from .metrics import default_registry, default_collector

    exporter = PrometheusExporter(
        host="0.0.0.0",
        port=9090,
        registry=default_registry,
        collector=default_collector
    )

    try:
        asyncio.run(exporter.run_forever())
    except KeyboardInterrupt:
        print("\n正在停止 Exporter...")
        asyncio.run(exporter.stop())
        print("Exporter 已停止")
