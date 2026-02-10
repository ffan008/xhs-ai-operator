"""
Prometheus 指标收集模块

提供性能指标收集、Prometheus exporter 等功能。
"""

import time
import threading
from functools import wraps
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
import psutil


# ============================================================================
# 指标类型
# ============================================================================

class MetricType:
    """指标类型"""
    COUNTER = "counter"       # 计数器（只增不减）
    GAUGE = "gauge"           # 仪表（可增可减）
    HISTOGRAM = "histogram"   # 直方图（分布）
    SUMMARY = "summary"       # 摘要（统计）
    UNTYPED = "untyped"       # 无类型


# ============================================================================
# 指标数据类
# ============================================================================

@dataclass
class Metric:
    """基础指标"""
    name: str                           # 指标名称
    type: str                           # 指标类型
    help: str                           # 帮助文本
    value: float = 0.0                  # 当前值
    labels: Dict[str, str] = field(default_factory=dict)  # 标签
    timestamp: float = field(default_factory=time.time)  # 时间戳


@dataclass
class Histogram:
    """直方图指标"""
    name: str
    help: str
    buckets: List[float]                # 桶边界
    counts: Dict[float, int] = field(default_factory=dict)  # 桶计数
    sum: float = 0.0                    # 总和
    count: int = 0                      # 总数
    labels: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """初始化桶"""
        for bucket in self.buckets:
            self.counts[bucket] = 0

    def observe(self, value: float) -> None:
        """
        观察一个值

        Args:
            value: 观察值
        """
        self.sum += value
        self.count += 1

        # 更新桶计数
        for bucket in self.buckets:
            if value <= bucket:
                self.counts[bucket] += 1

    def get_quantile(self, q: float) -> float:
        """
        计算分位数（估算）

        Args:
            q: 分位数 (0-1)

        Returns:
            分位数值
        """
        if self.count == 0:
            return 0.0

        target = self.count * q
        accumulated = 0

        for bucket in sorted(self.buckets):
            accumulated += self.counts[bucket]
            if accumulated >= target:
                return bucket

        return float('inf')


@dataclass
class Summary:
    """摘要指标"""
    name: str
    help: str
    values: deque = field(default_factory=lambda: deque(maxlen=1000))  # 值队列
    count: int = 0                      # 总数
    sum: float = 0.0                    # 总和
    labels: Dict[str, str] = field(default_factory=dict)

    def observe(self, value: float) -> None:
        """
        观察一个值

        Args:
            value: 观察值
        """
        self.values.append(value)
        self.count += 1
        self.sum += value

    def get_quantile(self, q: float) -> float:
        """
        计算分位数

        Args:
            q: 分位数 (0-1)

        Returns:
            分位数值
        """
        if not self.values:
            return 0.0

        sorted_values = sorted(self.values)
        index = int(len(sorted_values) * q)
        return sorted_values[min(index, len(sorted_values) - 1)]


# ============================================================================
# 指标注册表
# ============================================================================

class MetricRegistry:
    """指标注册表"""

    def __init__(self):
        """初始化注册表"""
        self._metrics: Dict[str, Metric] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._summaries: Dict[str, Summary] = {}
        self._lock = threading.Lock()

        # 默认桶
        self._default_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]

    def counter(
        self,
        name: str,
        help_text: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Metric:
        """
        创建或获取计数器

        Args:
            name: 指标名称
            help_text: 帮助文本
            labels: 标签

        Returns:
            指标对象
        """
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Metric(
                    name=name,
                    type=MetricType.COUNTER,
                    help=help_text,
                    labels=labels or {}
                )
            return self._metrics[name]

    def gauge(
        self,
        name: str,
        help_text: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Metric:
        """
        创建或获取仪表

        Args:
            name: 指标名称
            help_text: 帮助文本
            labels: 标签

        Returns:
            指标对象
        """
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Metric(
                    name=name,
                    type=MetricType.GAUGE,
                    help=help_text,
                    labels=labels or {}
                )
            return self._metrics[name]

    def histogram(
        self,
        name: str,
        help_text: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Histogram:
        """
        创建或获取直方图

        Args:
            name: 指标名称
            help_text: 帮助文本
            buckets: 桶边界
            labels: 标签

        Returns:
            直方图对象
        """
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(
                    name=name,
                    help=help_text,
                    buckets=buckets or self._default_buckets,
                    labels=labels or {}
                )
            return self._histograms[name]

    def summary(
        self,
        name: str,
        help_text: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Summary:
        """
        创建或获取摘要

        Args:
            name: 指标名称
            help_text: 帮助文本
            labels: 标签

        Returns:
            摘要对象
        """
        with self._lock:
            if name not in self._summaries:
                self._summaries[name] = Summary(
                    name=name,
                    help=help_text,
                    labels=labels or {}
                )
            return self._summaries[name]

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """
        增加计数器

        Args:
            name: 指标名称
            value: 增加值
            labels: 标签
        """
        with self._lock:
            if name in self._metrics:
                self._metrics[name].value += value
                if labels:
                    self._metrics[name].labels.update(labels)

    def set(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        设置仪表值

        Args:
            name: 指标名称
            value: 设置值
            labels: 标签
        """
        with self._lock:
            if name in self._metrics:
                self._metrics[name].value = value
                if labels:
                    self._metrics[name].labels.update(labels)

    def observe(self, name: str, value: float) -> None:
        """
        观察值（直方图/摘要）

        Args:
            name: 指标名称
            value: 观察值
        """
        with self._lock:
            if name in self._histograms:
                self._histograms[name].observe(value)
            if name in self._summaries:
                self._summaries[name].observe(value)

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有指标

        Returns:
            指标字典
        """
        with self._lock:
            result = {
                "metrics": dict(self._metrics),
                "histograms": dict(self._histograms),
                "summaries": dict(self._summaries)
            }
            return result

    def export_prometheus(self) -> str:
        """
        导出 Prometheus 格式

        Returns:
            Prometheus 格式文本
        """
        lines = []

        with self._lock:
            # 导出指标
            for metric in self._metrics.values():
                # HELP
                lines.append(f"# HELP {metric.name} {metric.help}")

                # TYPE
                lines.append(f"# TYPE {metric.name} {metric.type}")

                # 标签
                label_str = ""
                if metric.labels:
                    label_pairs = [f'{k}="{v}"' for k, v in metric.labels.items()]
                    label_str = "{" + ",".join(label_pairs) + "}"

                # VALUE
                lines.append(f"{metric.name}{label_str} {metric.value}")

            # 导出直方图
            for hist in self._histograms.values():
                # HELP
                lines.append(f"# HELP {hist.name} {hist.help}")

                # TYPE
                lines.append(f"# TYPE {hist.name} {MetricType.HISTOGRAM}")

                # 标签
                label_str = ""
                if hist.labels:
                    label_pairs = [f'{k}="{v}"' for k, v in hist.labels.items()]
                    label_str = "{" + ",".join(label_pairs) + "}"

                # 桶
                for bucket in sorted(hist.buckets):
                    bucket_metric = f"{hist.name}_bucket{label_str}"
                    lines.append(f'{bucket_metric}{{le="{bucket}"}} {hist.counts[bucket]}')

                # +Inf 桶
                bucket_metric = f"{hist.name}_bucket{label_str}"
                lines.append(f'{bucket_metric}{{le="+Inf"}} {hist.count}')

                # 总和和计数
                lines.append(f"{hist.name}_sum{label_str} {hist.sum}")
                lines.append(f"{hist.name}_count{label_str} {hist.count}")

            # 导出摘要
            for summary in self._summaries.values():
                # HELP
                lines.append(f"# HELP {summary.name} {summary.help}")

                # TYPE
                lines.append(f"# TYPE {summary.name} {MetricType.SUMMARY}")

                # 标签
                label_str = ""
                if summary.labels:
                    label_pairs = [f'{k}="{v}"' for k, v in summary.labels.items()]
                    label_str = "{" + ",".join(label_pairs) + "}"

                # 分位数
                for q in [0.5, 0.9, 0.95, 0.99]:
                    quantile_value = summary.get_quantile(q)
                    quantile_metric = f"{summary.name}{label_str}"
                    lines.append(f'{quantile_metric}{{quantile="{q}"}} {quantile_value}')

                # 总和和计数
                lines.append(f"{summary.name}_sum{label_str} {summary.sum}")
                lines.append(f"{summary.name}_count{label_str} {summary.count}")

        return "\n".join(lines)


# ============================================================================
# 性能收集器
# ============================================================================

class PerformanceCollector:
    """性能收集器"""

    def __init__(self, registry: MetricRegistry):
        """
        初始化性能收集器

        Args:
            registry: 指标注册表
        """
        self.registry = registry
        self._start_time = time.time()
        self._last_cpu = psutil.cpu_percent()
        self._last_net = psutil.net_io_counters()

        # 注册系统指标
        self._register_system_metrics()

    def _register_system_metrics(self) -> None:
        """注册系统指标"""
        # CPU
        self.registry.gauge("system_cpu_percent", "CPU 使用百分比")
        self.registry.gauge("system_cpu_count", "CPU 核心数")

        # 内存
        self.registry.gauge("system_memory_percent", "内存使用百分比")
        self.registry.gauge("system_memory_used_bytes", "已使用内存（字节）")
        self.registry.gauge("system_memory_total_bytes", "总内存（字节）")

        # 磁盘
        self.registry.gauge("system_disk_percent", "磁盘使用百分比")
        self.registry.gauge("system_disk_used_bytes", "已使用磁盘（字节）")
        self.registry.gauge("system_disk_total_bytes", "总磁盘（字节）")

        # 网络
        self.registry.counter("system_network_sent_bytes", "发送字节数")
        self.registry.counter("system_network_recv_bytes", "接收字节数")

        # 进程
        self.registry.gauge("process_memory_bytes", "进程内存（字节）")
        self.registry.gauge("process_cpu_percent", "进程 CPU 使用百分比")
        self.registry.gauge("process_num_threads", "进程线程数")
        self.registry.gauge("process_num_fds", "进程文件描述符数")

        # 应用
        self.registry.counter("app_requests_total", "总请求数")
        self.registry.counter("app_errors_total", "总错误数")
        self.registry.histogram("app_request_duration_seconds", "请求耗时（秒）")
        self.registry.gauge("app_active_requests", "活跃请求数")

    def collect(self) -> None:
        """收集系统指标"""
        # CPU
        cpu_percent = psutil.cpu_percent()
        cpu_count = psutil.cpu_count()
        self.registry.set("system_cpu_percent", cpu_percent)
        self.registry.set("system_cpu_count", cpu_count)

        # 内存
        memory = psutil.virtual_memory()
        self.registry.set("system_memory_percent", memory.percent)
        self.registry.set("system_memory_used_bytes", memory.used)
        self.registry.set("system_memory_total_bytes", memory.total)

        # 磁盘
        disk = psutil.disk_usage('/')
        self.registry.set("system_disk_percent", disk.percent)
        self.registry.set("system_disk_used_bytes", disk.used)
        self.registry.set("system_disk_total_bytes", disk.total)

        # 网络
        net = psutil.net_io_counters()
        if self._last_net:
            sent_delta = net.bytes_sent - self._last_net.bytes_sent
            recv_delta = net.bytes_recv - self._last_net.bytes_recv
            self.registry.increment("system_network_sent_bytes", sent_delta)
            self.registry.increment("system_network_recv_bytes", recv_delta)
        self._last_net = net

        # 进程
        process = psutil.Process()
        self.registry.set("process_memory_bytes", process.memory_info().rss)
        self.registry.set("process_cpu_percent", process.cpu_percent())
        self.registry.set("process_num_threads", process.num_threads())
        try:
            self.registry.set("process_num_fds", process.num_fds())
        except:
            pass  # Windows 不支持

        # 运行时间
        uptime = time.time() - self._start_time
        if "app_uptime_seconds" not in self.registry._metrics:
            self.registry.gauge("app_uptime_seconds", "应用运行时间（秒）")
        self.registry.set("app_uptime_seconds", uptime)


# ============================================================================
# 装饰器
# ============================================================================

def track_requests(registry: MetricRegistry):
    """
    请求追踪装饰器

    Args:
        registry: 指标注册表

    使用:
        @track_requests(registry)
        def my_handler():
            return "ok"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 增加活跃请求
            registry.increment("app_active_requests", 1)

            start_time = time.time()
            try:
                result = func(*args, **kwargs)

                # 记录请求
                registry.increment("app_requests_total")
                duration = time.time() - start_time
                registry.observe("app_request_duration_seconds", duration)

                return result

            except Exception as e:
                # 记录错误
                registry.increment("app_errors_total")
                duration = time.time() - start_time
                registry.observe("app_request_duration_seconds", duration)
                raise

            finally:
                # 减少活跃请求
                registry.increment("app_active_requests", -1)

        return wrapper
    return decorator


def track_async_requests(registry: MetricRegistry):
    """
    异步请求追踪装饰器

    Args:
        registry: 指标注册表

    使用:
        @track_async_requests(registry)
        async def my_handler():
            return "ok"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 增加活跃请求
            registry.increment("app_active_requests", 1)

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)

                # 记录请求
                registry.increment("app_requests_total")
                duration = time.time() - start_time
                registry.observe("app_request_duration_seconds", duration)

                return result

            except Exception as e:
                # 记录错误
                registry.increment("app_errors_total")
                duration = time.time() - start_time
                registry.observe("app_request_duration_seconds", duration)
                raise

            finally:
                # 减少活跃请求
                registry.increment("app_active_requests", -1)

        return wrapper
    return decorator


# ============================================================================
# 默认实例
# ============================================================================

# 默认注册表
default_registry = MetricRegistry()

# 默认性能收集器
default_collector = PerformanceCollector(default_registry)


# ============================================================================
# 便捷函数
# ============================================================================

def increment_counter(name: str, value: float = 1.0) -> None:
    """增加计数器"""
    default_registry.increment(name, value)


def set_gauge(name: str, value: float) -> None:
    """设置仪表值"""
    default_registry.set(name, value)


def observe_histogram(name: str, value: float) -> None:
    """观察直方图值"""
    default_registry.observe(name, value)


def collect_metrics() -> None:
    """收集系统指标"""
    default_collector.collect()


def export_metrics() -> str:
    """导出 Prometheus 格式"""
    return default_registry.export_prometheus()


# 导出
__all__ = [
    'MetricType',
    'Metric',
    'Histogram',
    'Summary',
    'MetricRegistry',
    'PerformanceCollector',
    'track_requests',
    'track_async_requests',
    'default_registry',
    'default_collector',
    'increment_counter',
    'set_gauge',
    'observe_histogram',
    'collect_metrics',
    'export_metrics'
]
