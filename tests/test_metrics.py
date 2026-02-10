"""
Prometheus 监控模块单元测试
"""

import pytest
import asyncio
import time
import psutil
from pathlib import Path
from datetime import datetime
from typing import List
from unittest.mock import Mock, patch, MagicMock

# 添加父目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.metrics import (
    MetricType,
    Metric,
    Histogram,
    Summary,
    MetricRegistry,
    PerformanceCollector,
    track_requests,
    track_async_requests,
    default_registry,
    default_collector,
    increment_counter,
    set_gauge,
    observe_histogram,
    collect_metrics,
    export_metrics
)


# ============================================================================
# 直方图测试
# ============================================================================

class TestHistogram:
    """测试直方图"""

    def test_create_histogram(self):
        """测试创建直方图"""
        hist = Histogram(
            name="test_histogram",
            help="Test histogram",
            buckets=[1.0, 5.0, 10.0]
        )

        assert hist.name == "test_histogram"
        assert len(hist.buckets) == 3
        assert hist.count == 0
        print("✅ 创建直方图成功")

    def test_observe(self):
        """测试观察值"""
        hist = Histogram(
            name="test_histogram",
            help="Test histogram",
            buckets=[1.0, 5.0, 10.0]
        )

        hist.observe(0.5)
        hist.observe(2.0)
        hist.observe(7.0)

        assert hist.count == 3
        assert hist.sum == 9.5
        print("✅ 观察值正确")

    def test_quantile(self):
        """测试分位数"""
        hist = Histogram(
            name="test_histogram",
            help="Test histogram",
            buckets=[1.0, 5.0, 10.0]
        )

        # 添加值
        for i in range(10):
            hist.observe(float(i))

        # P50 应该在 5 左右
        p50 = hist.get_quantile(0.5)
        assert p50 <= 5.0
        print("✅ 分位数计算正确")


# ============================================================================
# 摘要测试
# ============================================================================

class TestSummary:
    """测试摘要"""

    def test_create_summary(self):
        """测试创建摘要"""
        summary = Summary(
            name="test_summary",
            help="Test summary"
        )

        assert summary.name == "test_summary"
        assert summary.count == 0
        print("✅ 创建摘要成功")

    def test_observe(self):
        """测试观察值"""
        summary = Summary(
            name="test_summary",
            help="Test summary"
        )

        summary.observe(1.0)
        summary.observe(2.0)
        summary.observe(3.0)

        assert summary.count == 3
        assert summary.sum == 6.0
        print("✅ 观察值正确")

    def test_quantile(self):
        """测试分位数"""
        summary = Summary(
            name="test_summary",
            help="Test summary"
        )

        # 添加值
        for i in range(1, 101):
            summary.observe(float(i))

        # P50 应该是 50
        p50 = summary.get_quantile(0.5)
        assert 45 <= p50 <= 55
        print("✅ 分位数计算正确")


# ============================================================================
# 指标注册表测试
# ============================================================================

class TestMetricRegistry:
    """测试指标注册表"""

    def test_counter(self):
        """测试计数器"""
        registry = MetricRegistry()
        counter = registry.counter("test_counter", "Test counter")

        assert counter.name == "test_counter"
        assert counter.type == MetricType.COUNTER
        assert counter.value == 0
        print("✅ 计数器正确")

    def test_gauge(self):
        """测试仪表"""
        registry = MetricRegistry()
        gauge = registry.gauge("test_gauge", "Test gauge")

        assert gauge.name == "test_gauge"
        assert gauge.type == MetricType.GAUGE
        print("✅ 仪表正确")

    def test_histogram(self):
        """测试直方图"""
        registry = MetricRegistry()
        hist = registry.histogram("test_hist", "Test histogram")

        assert hist.name == "test_hist"
        assert hist.count == 0
        print("✅ 直方图正确")

    def test_summary(self):
        """测试摘要"""
        registry = MetricRegistry()
        summary = registry.summary("test_summary", "Test summary")

        assert summary.name == "test_summary"
        assert summary.count == 0
        print("✅ 摘要正确")

    def test_increment(self):
        """测试增加"""
        registry = MetricRegistry()
        registry.counter("test_counter", "Test counter")

        registry.increment("test_counter", 1.5)
        assert registry._metrics["test_counter"].value == 1.5

        registry.increment("test_counter", 2.5)
        assert registry._metrics["test_counter"].value == 4.0
        print("✅ 增加正确")

    def test_set(self):
        """测试设置"""
        registry = MetricRegistry()
        registry.gauge("test_gauge", "Test gauge")

        registry.set("test_gauge", 42.0)
        assert registry._metrics["test_gauge"].value == 42.0

        registry.set("test_gauge", 100.0)
        assert registry._metrics["test_gauge"].value == 100.0
        print("✅ 设置正确")

    def test_observe(self):
        """测试观察"""
        registry = MetricRegistry()
        registry.histogram("test_hist", "Test histogram")

        registry.observe("test_hist", 5.0)
        assert registry._histograms["test_hist"].count == 1
        print("✅ 观察正确")

    def test_export_prometheus(self):
        """测试导出 Prometheus 格式"""
        registry = MetricRegistry()

        # 添加指标
        registry.counter("requests_total", "Total requests")
        registry.gauge("temperature", "Current temperature")
        registry.histogram("response_time", "Response time")

        # 设置值
        registry.increment("requests_total", 100)
        registry.set("temperature", 25.5)
        registry.observe("response_time", 0.5)

        # 导出
        exported = registry.export_prometheus()

        assert "# HELP requests_total Total requests" in exported
        assert "# TYPE requests_total counter" in exported
        assert "requests_total 100.0" in exported
        assert "temperature 25.5" in exported
        assert "response_time_bucket" in exported
        print("✅ Prometheus 导出正确")


# ============================================================================
# 性能收集器测试
# ============================================================================

class TestPerformanceCollector:
    """测试性能收集器"""

    def test_initialization(self):
        """测试初始化"""
        registry = MetricRegistry()
        collector = PerformanceCollector(registry)

        assert collector.registry is registry
        print("✅ 初始化正确")

    def test_collect(self):
        """测试收集"""
        registry = MetricRegistry()
        collector = PerformanceCollector(registry)

        # 收集
        collector.collect()

        # 验证指标已设置
        assert registry._metrics["system_cpu_percent"].value >= 0
        assert registry._metrics["system_memory_percent"].value >= 0
        assert registry._metrics["system_cpu_count"].value > 0
        print("✅ 收集正确")


# ============================================================================
# 装饰器测试
# ============================================================================

class TestDecorators:
    """测试装饰器"""

    def test_track_requests(self):
        """测试请求追踪"""
        registry = MetricRegistry()
        registry.counter("app_requests_total", "Total requests")
        registry.histogram("app_request_duration_seconds", "Request duration")
        registry.gauge("app_active_requests", "Active requests")

        @track_requests(registry)
        def handler():
            time.sleep(0.01)
            return "ok"

        # 调用
        result = handler()

        assert result == "ok"
        assert registry._metrics["app_requests_total"].value == 1
        assert registry._metrics["app_active_requests"].value == 0  # 已完成
        print("✅ 请求追踪正确")

    def test_track_requests_error(self):
        """测试请求追踪错误"""
        registry = MetricRegistry()
        registry.counter("app_requests_total", "Total requests")
        registry.counter("app_errors_total", "Total errors")
        registry.histogram("app_request_duration_seconds", "Request duration")
        registry.gauge("app_active_requests", "Active requests")

        @track_requests(registry)
        def failing_handler():
            raise ValueError("Test error")

        # 调用
        with pytest.raises(ValueError):
            failing_handler()

        # 验证错误已记录
        assert registry._metrics["app_errors_total"].value == 1
        assert registry._metrics["app_active_requests"].value == 0
        print("✅ 错误追踪正确")


# ============================================================================
# 便捷函数测试
# ============================================================================

class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_increment_counter(self):
        """测试增加计数器"""
        # 清空注册表
        default_registry._metrics.clear()

        default_registry.counter("test_counter", "Test counter")
        increment_counter("test_counter", 5.0)

        assert default_registry._metrics["test_counter"].value == 5.0
        print("✅ 增加计数器正确")

    def test_set_gauge(self):
        """测试设置仪表"""
        # 清空注册表
        default_registry._metrics.clear()

        default_registry.gauge("test_gauge", "Test gauge")
        set_gauge("test_gauge", 42.0)

        assert default_registry._metrics["test_gauge"].value == 42.0
        print("✅ 设置仪表正确")

    def test_observe_histogram(self):
        """测试观察直方图"""
        # 清空注册表
        default_registry._histograms.clear()

        default_registry.histogram("test_hist", "Test histogram")
        observe_histogram("test_hist", 3.5)

        assert default_registry._histograms["test_hist"].count == 1
        print("✅ 观察直方图正确")

    def test_collect_metrics(self):
        """测试收集指标"""
        # 收集指标
        collect_metrics()

        # 验证系统指标已收集
        assert len(default_registry._metrics) > 0
        print("✅ 收集指标正确")

    def test_export_metrics(self):
        """测试导出指标"""
        exported = export_metrics()

        assert "# HELP" in exported
        assert "# TYPE" in exported
        print("✅ 导出指标正确")


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试"""

    def test_full_metrics_workflow(self):
        """测试完整指标工作流"""
        # 创建注册表
        registry = MetricRegistry()

        # 注册指标
        registry.counter("http_requests_total", "Total HTTP requests", labels={"method": "GET"})
        registry.histogram("http_request_duration_seconds", "HTTP request duration")
        registry.gauge("active_connections", "Active connections")

        # 模拟请求
        registry.increment("http_requests_total", 1)
        registry.observe("http_request_duration_seconds", 0.1)
        registry.set("active_connections", 5)

        # 第二个请求
        registry.increment("http_requests_total", 1)
        registry.observe("http_request_duration_seconds", 0.2)

        # 验证
        assert registry._metrics["http_requests_total"].value == 2
        assert registry._histograms["http_request_duration_seconds"].count == 2
        assert registry._metrics["active_connections"].value == 5

        # 导出
        exported = registry.export_prometheus()
        assert "http_requests_total" in exported
        assert "http_request_duration_seconds" in exported

        print("✅ 完整工作流正确")

    def test_performance_collector_workflow(self):
        """测试性能收集器工作流"""
        registry = MetricRegistry()
        collector = PerformanceCollector(registry)

        # 收集多次
        for _ in range(3):
            collector.collect()
            time.sleep(0.1)

        # 验证指标
        assert registry._metrics["app_uptime_seconds"].value > 0

        # 导出
        exported = registry.export_prometheus()
        assert "system_cpu_percent" in exported
        assert "system_memory_percent" in exported

        print("✅ 性能收集器工作流正确")


# ============================================================================
# 运行所有测试
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行 Prometheus 监控测试...\n")

    print("="*60)
    print("测试直方图")
    print("="*60)
    TestHistogram().test_create_histogram()
    TestHistogram().test_observe()
    TestHistogram().test_quantile()

    print("\n" + "="*60)
    print("测试摘要")
    print("="*60)
    TestSummary().test_create_summary()
    TestSummary().test_observe()
    TestSummary().test_quantile()

    print("\n" + "="*60)
    print("测试指标注册表")
    print("="*60)
    TestMetricRegistry().test_counter()
    TestMetricRegistry().test_gauge()
    TestMetricRegistry().test_histogram()
    TestMetricRegistry().test_summary()
    TestMetricRegistry().test_increment()
    TestMetricRegistry().test_set()
    TestMetricRegistry().test_observe()
    TestMetricRegistry().test_export_prometheus()

    print("\n" + "="*60)
    print("测试性能收集器")
    print("="*60)
    TestPerformanceCollector().test_initialization()
    TestPerformanceCollector().test_collect()

    print("\n" + "="*60)
    print("测试装饰器")
    print("="*60)
    TestDecorators().test_track_requests()
    TestDecorators().test_track_requests_error()

    print("\n" + "="*60)
    print("测试便捷函数")
    print("="*60)
    TestConvenienceFunctions().test_increment_counter()
    TestConvenienceFunctions().test_set_gauge()
    TestConvenienceFunctions().test_observe_histogram()
    TestConvenienceFunctions().test_collect_metrics()
    TestConvenienceFunctions().test_export_metrics()

    print("\n" + "="*60)
    print("测试集成")
    print("="*60)
    TestIntegration().test_full_metrics_workflow()
    TestIntegration().test_performance_collector_workflow()

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
