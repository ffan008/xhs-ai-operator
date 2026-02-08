"""
健康检查模块

提供服务健康检查、存活检查、就绪检查等功能。
"""

import os
import sys
import psutil
import shutil
import asyncio
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable
from collections import deque
from urllib.parse import urlparse
import json
import sqlite3
import socket
import requests
from pathlib import Path


# ============================================================================
# 健康状态
# ============================================================================

class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"       # 健康
    DEGRADED = "degraded"     # 降级
    UNHEALTHY = "unhealthy"   # 不健康
    UNKNOWN = "unknown"       # 未知


# ============================================================================
# 检查结果
# ============================================================================

@dataclass
class CheckResult:
    """检查结果"""
    name: str                              # 检查项名称
    status: HealthStatus                   # 状态
    message: str = ""                      # 消息
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳
    duration_ms: float = 0.0               # 耗时（毫秒）
    critical: bool = False                 # 是否关键检查

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": round(self.duration_ms, 2),
            "critical": self.critical
        }


# ============================================================================
# 健康检查基类
# ============================================================================

class HealthCheck(ABC):
    """健康检查基类"""

    def __init__(self, name: str, critical: bool = True):
        """
        初始化健康检查

        Args:
            name: 检查项名称
            critical: 是否关键检查
        """
        self.name = name
        self.critical = critical
        self._last_result: Optional[CheckResult] = None
        self._history: deque = deque(maxlen=100)

    @abstractmethod
    async def check(self) -> CheckResult:
        """
        执行健康检查

        Returns:
            检查结果
        """
        pass

    def get_last_result(self) -> Optional[CheckResult]:
        """获取上次检查结果"""
        return self._last_result

    def get_history(self, limit: int = 10) -> List[CheckResult]:
        """
        获取历史记录

        Args:
            limit: 返回数量

        Returns:
            历史记录列表
        """
        return list(self._history)[-limit:]

    def _save_result(self, result: CheckResult) -> None:
        """保存结果"""
        self._last_result = result
        self._history.append(result)


# ============================================================================
# 磁盘空间检查
# ============================================================================

class DiskSpaceHealthCheck(HealthCheck):
    """磁盘空间检查"""

    def __init__(
        self,
        path: str = "/",
        warning_threshold: float = 80.0,
        critical_threshold: float = 90.0,
        critical: bool = True
    ):
        """
        初始化磁盘空间检查

        Args:
            path: 检查路径
            warning_threshold: 警告阈值（百分比）
            critical_threshold: 严重阈值（百分比）
            critical: 是否关键检查
        """
        super().__init__("disk_space", critical)
        self.path = path
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    async def check(self) -> CheckResult:
        """检查磁盘空间"""
        start_time = time.time()

        try:
            # 获取磁盘使用情况
            usage = psutil.disk_usage(self.path)

            # 计算使用百分比
            percent_used = (usage.used / usage.total) * 100
            gb_free = usage.free / (1024 ** 3)
            gb_total = usage.total / (1024 ** 3)
            gb_used = usage.used / (1024 ** 3)

            details = {
                "path": self.path,
                "percent_used": round(percent_used, 2),
                "gb_free": round(gb_free, 2),
                "gb_used": round(gb_used, 2),
                "gb_total": round(gb_total, 2),
                "warning_threshold": self.warning_threshold,
                "critical_threshold": self.critical_threshold
            }

            # 判断状态
            if percent_used >= self.critical_threshold:
                status = HealthStatus.UNHEALTHY
                message = f"磁盘空间不足: {percent_used:.1f}% 已使用"
            elif percent_used >= self.warning_threshold:
                status = HealthStatus.DEGRADED
                message = f"磁盘空间警告: {percent_used:.1f}% 已使用"
            else:
                status = HealthStatus.HEALTHY
                message = f"磁盘空间正常: {percent_used:.1f}% 已使用"

            duration_ms = (time.time() - start_time) * 1000

            result = CheckResult(
                name=self.name,
                status=status,
                message=message,
                details=details,
                duration_ms=duration_ms,
                critical=self.critical
            )

            self._save_result(result)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"检查失败: {str(e)}",
                duration_ms=duration_ms,
                critical=self.critical
            )
            self._save_result(result)
            return result


# ============================================================================
# 内存检查
# ============================================================================

class MemoryHealthCheck(HealthCheck):
    """内存检查"""

    def __init__(
        self,
        warning_threshold: float = 80.0,
        critical_threshold: float = 90.0,
        critical: bool = True
    ):
        """
        初始化内存检查

        Args:
            warning_threshold: 警告阈值（百分比）
            critical_threshold: 严重阈值（百分比）
            critical: 是否关键检查
        """
        super().__init__("memory", critical)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    async def check(self) -> CheckResult:
        """检查内存使用"""
        start_time = time.time()

        try:
            # 获取内存使用情况
            mem = psutil.virtual_memory()

            percent_used = mem.percent
            gb_available = mem.available / (1024 ** 3)
            gb_total = mem.total / (1024 ** 3)
            gb_used = mem.used / (1024 ** 3)

            details = {
                "percent_used": round(percent_used, 2),
                "gb_available": round(gb_available, 2),
                "gb_used": round(gb_used, 2),
                "gb_total": round(gb_total, 2),
                "warning_threshold": self.warning_threshold,
                "critical_threshold": self.critical_threshold
            }

            # 判断状态
            if percent_used >= self.critical_threshold:
                status = HealthStatus.UNHEALTHY
                message = f"内存不足: {percent_used:.1f}% 已使用"
            elif percent_used >= self.warning_threshold:
                status = HealthStatus.DEGRADED
                message = f"内存警告: {percent_used:.1f}% 已使用"
            else:
                status = HealthStatus.HEALTHY
                message = f"内存正常: {percent_used:.1f}% 已使用"

            duration_ms = (time.time() - start_time) * 1000

            result = CheckResult(
                name=self.name,
                status=status,
                message=message,
                details=details,
                duration_ms=duration_ms,
                critical=self.critical
            )

            self._save_result(result)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"检查失败: {str(e)}",
                duration_ms=duration_ms,
                critical=self.critical
            )
            self._save_result(result)
            return result


# ============================================================================
# CPU 检查
# ============================================================================

class CPUHealthCheck(HealthCheck):
    """CPU 检查"""

    def __init__(
        self,
        warning_threshold: float = 70.0,
        critical_threshold: float = 90.0,
        interval: float = 1.0,
        critical: bool = False
    ):
        """
        初始化 CPU 检查

        Args:
            warning_threshold: 警告阈值（百分比）
            critical_threshold: 严重阈值（百分比）
            interval: 采样间隔（秒）
            critical: 是否关键检查
        """
        super().__init__("cpu", critical)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.interval = interval

    async def check(self) -> CheckResult:
        """检查 CPU 使用"""
        start_time = time.time()

        try:
            # 获取 CPU 使用率（需要采样间隔）
            percent = psutil.cpu_percent(interval=self.interval)

            # 获取 CPU 数量
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)

            details = {
                "percent_used": round(percent, 2),
                "cpu_count": cpu_count,
                "cpu_count_logical": cpu_count_logical,
                "warning_threshold": self.warning_threshold,
                "critical_threshold": self.critical_threshold
            }

            # 判断状态
            if percent >= self.critical_threshold:
                status = HealthStatus.UNHEALTHY
                message = f"CPU 负载过高: {percent:.1f}%"
            elif percent >= self.warning_threshold:
                status = HealthStatus.DEGRADED
                message = f"CPU 负载警告: {percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"CPU 负载正常: {percent:.1f}%"

            duration_ms = (time.time() - start_time) * 1000

            result = CheckResult(
                name=self.name,
                status=status,
                message=message,
                details=details,
                duration_ms=duration_ms,
                critical=self.critical
            )

            self._save_result(result)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"检查失败: {str(e)}",
                duration_ms=duration_ms,
                critical=self.critical
            )
            self._save_result(result)
            return result


# ============================================================================
# 进程检查
# ============================================================================

class ProcessHealthCheck(HealthCheck):
    """进程检查"""

    def __init__(self, pid: Optional[int] = None, critical: bool = True):
        """
        初始化进程检查

        Args:
            pid: 进程 ID，None 表示当前进程
            critical: 是否关键检查
        """
        super().__init__("process", critical)
        self.pid = pid or os.getpid()

    async def check(self) -> CheckResult:
        """检查进程状态"""
        start_time = time.time()

        try:
            # 检查进程是否存在
            if not psutil.pid_exists(self.pid):
                result = CheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"进程 {self.pid} 不存在",
                    duration_ms=(time.time() - start_time) * 1000,
                    critical=self.critical
                )
                self._save_result(result)
                return result

            # 获取进程信息
            process = psutil.Process(self.pid)

            details = {
                "pid": self.pid,
                "name": process.name(),
                "status": process.status(),
                "cpu_percent": round(process.cpu_percent(interval=0.1), 2),
                "memory_mb": round(process.memory_info().rss / (1024 ** 2), 2),
                "num_threads": process.num_threads(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
            }

            result = CheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message=f"进程运行正常: {process.name()} (PID: {self.pid})",
                details=details,
                duration_ms=(time.time() - start_time) * 1000,
                critical=self.critical
            )

            self._save_result(result)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"检查失败: {str(e)}",
                duration_ms=duration_ms,
                critical=self.critical
            )
            self._save_result(result)
            return result


# ============================================================================
# 数据库检查
# ============================================================================

class DatabaseHealthCheck(HealthCheck):
    """数据库检查"""

    def __init__(
        self,
        db_path: str,
        critical: bool = True,
        timeout: float = 5.0
    ):
        """
        初始化数据库检查

        Args:
            db_path: 数据库路径
            critical: 是否关键检查
            timeout: 超时时间（秒）
        """
        super().__init__("database", critical)
        self.db_path = db_path
        self.timeout = timeout

    async def check(self) -> CheckResult:
        """检查数据库连接"""
        start_time = time.time()

        try:
            # 检查数据库文件是否存在
            if not os.path.exists(self.db_path):
                result = CheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"数据库文件不存在: {self.db_path}",
                    duration_ms=(time.time() - start_time) * 1000,
                    critical=self.critical
                )
                self._save_result(result)
                return result

            # 尝试连接数据库
            conn = sqlite3.connect(self.db_path, timeout=self.timeout)
            cursor = conn.cursor()

            # 执行简单查询
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

            conn.close()

            # 获取数据库大小
            db_size = os.path.getsize(self.db_path) / (1024 ** 2)

            details = {
                "db_path": self.db_path,
                "db_size_mb": round(db_size, 2),
                "query_result": result,
                "timeout": self.timeout
            }

            duration_ms = (time.time() - start_time) * 1000

            check_result = CheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message=f"数据库连接正常",
                details=details,
                duration_ms=duration_ms,
                critical=self.critical
            )

            self._save_result(check_result)
            return check_result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"数据库检查失败: {str(e)}",
                duration_ms=duration_ms,
                critical=self.critical
            )
            self._save_result(result)
            return result


# ============================================================================
# API 端点检查
# ============================================================================

class APIHealthCheck(HealthCheck):
    """API 端点检查"""

    def __init__(
        self,
        url: str,
        expected_status: int = 200,
        timeout: float = 5.0,
        critical: bool = True
    ):
        """
        初始化 API 检查

        Args:
            url: API 端点 URL
            expected_status: 期望的 HTTP 状态码
            timeout: 超时时间（秒）
            critical: 是否关键检查
        """
        super().__init__("api", critical)
        self.url = url
        self.expected_status = expected_status
        self.timeout = timeout

    async def check(self) -> CheckResult:
        """检查 API 端点"""
        start_time = time.time()

        try:
            # 发送请求
            response = requests.get(self.url, timeout=self.timeout)

            response_time_ms = (time.time() - start_time) * 1000

            details = {
                "url": self.url,
                "status_code": response.status_code,
                "expected_status": self.expected_status,
                "response_time_ms": round(response_time_ms, 2),
                "timeout": self.timeout
            }

            # 判断状态
            if response.status_code == self.expected_status:
                status = HealthStatus.HEALTHY
                message = f"API 端点正常: {response.status_code}"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"API 端点异常: 期望 {self.expected_status}，实际 {response.status_code}"

            result = CheckResult(
                name=self.name,
                status=status,
                message=message,
                details=details,
                duration_ms=response_time_ms,
                critical=self.critical
            )

            self._save_result(result)
            return result

        except requests.exceptions.Timeout:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"API 端点超时: >{self.timeout}秒",
                details={"url": self.url, "timeout": self.timeout},
                duration_ms=duration_ms,
                critical=self.critical
            )
            self._save_result(result)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"API 检查失败: {str(e)}",
                details={"url": self.url},
                duration_ms=duration_ms,
                critical=self.critical
            )
            self._save_result(result)
            return result


# ============================================================================
# 自定义检查
# ============================================================================

class CustomHealthCheck(HealthCheck):
    """自定义健康检查"""

    def __init__(
        self,
        name: str,
        check_func: Callable[[], CheckResult],
        critical: bool = True
    ):
        """
        初始化自定义检查

        Args:
            name: 检查项名称
            check_func: 检查函数
            critical: 是否关键检查
        """
        super().__init__(name, critical)
        self.check_func = check_func

    async def check(self) -> CheckResult:
        """执行自定义检查"""
        start_time = time.time()

        try:
            result = self.check_func()
            result.duration_ms = (time.time() - start_time) * 1000
            self._save_result(result)
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"检查失败: {str(e)}",
                duration_ms=duration_ms,
                critical=self.critical
            )
            self._save_result(result)
            return result


# ============================================================================
# 健康检查器
# ============================================================================

class HealthChecker:
    """健康检查器"""

    def __init__(self, service_name: str = "service"):
        """
        初始化健康检查器

        Args:
            service_name: 服务名称
        """
        self.service_name = service_name
        self._checks: Dict[str, HealthCheck] = {}
        self._lock = threading.Lock()
        self._last_check_time: Optional[datetime] = None
        self._last_results: Dict[str, CheckResult] = {}
        self._check_history: deque = deque(maxlen=1000)

    def register_check(self, check: HealthCheck) -> None:
        """
        注册健康检查

        Args:
            check: 健康检查对象
        """
        with self._lock:
            self._checks[check.name] = check

    def unregister_check(self, name: str) -> None:
        """
        取消注册健康检查

        Args:
            name: 检查项名称
        """
        with self._lock:
            if name in self._checks:
                del self._checks[name]

    async def check_health(
        self,
        check_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行健康检查

        Args:
            check_name: 指定检查项，None 表示检查所有

        Returns:
            检查结果字典
        """
        start_time = time.time()

        if check_name:
            # 检查单个
            if check_name not in self._checks:
                return {
                    "status": "unknown",
                    "error": f"检查项不存在: {check_name}"
                }

            check = self._checks[check_name]
            result = await check.check()

            self._last_results[check_name] = result

            return {
                "service": self.service_name,
                "check": result.to_dict()
            }

        # 检查所有
        results = []
        overall_status = HealthStatus.HEALTHY

        for check in self._checks.values():
            result = await check.check()
            results.append(result.to_dict())
            self._last_results[check.name] = result

            # 更新整体状态
            if result.critical and result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        duration_ms = (time.time() - start_time) * 1000

        response = {
            "service": self.service_name,
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": round(duration_ms, 2),
            "checks": results
        }

        # 保存历史
        self._last_check_time = datetime.now()
        self._check_history.append(response)

        return response

    async def check_liveness(self) -> Dict[str, Any]:
        """
        存活检查

        Returns:
            存活状态
        """
        return {
            "service": self.service_name,
            "status": "alive",
            "timestamp": datetime.now().isoformat()
        }

    async def check_readiness(self) -> Dict[str, Any]:
        """
        就绪检查

        Returns:
            就绪状态
        """
        # 检查所有关键检查项
        for check in self._checks.values():
            if check.critical:
                result = await check.check()
                if result.status != HealthStatus.HEALTHY:
                    return {
                        "service": self.service_name,
                        "status": "not_ready",
                        "reason": f"{check.name}: {result.message}",
                        "timestamp": datetime.now().isoformat()
                    }

        return {
            "service": self.service_name,
            "status": "ready",
            "timestamp": datetime.now().isoformat()
        }

    def get_check_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取检查历史

        Args:
            limit: 返回数量

        Returns:
            历史记录列表
        """
        return list(self._check_history)[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息
        """
        total_checks = len(self._checks)
        critical_checks = sum(1 for c in self._checks.values() if c.critical)

        # 统计各状态数量
        status_counts = {
            HealthStatus.HEALTHY.value: 0,
            HealthStatus.DEGRADED.value: 0,
            HealthStatus.UNHEALTHY.value: 0,
            HealthStatus.UNKNOWN.value: 0
        }

        for result in self._last_results.values():
            status_counts[result.status.value] += 1

        return {
            "service": self.service_name,
            "total_checks": total_checks,
            "critical_checks": critical_checks,
            "status_counts": status_counts,
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None
        }


# ============================================================================
# 默认健康检查器
# ============================================================================

# 创建默认健康检查器
default_health_checker = HealthChecker("xhs-ai-operator")

# 注册默认检查项
default_health_checker.register_check(DiskSpaceHealthCheck())
default_health_checker.register_check(MemoryHealthCheck())
default_health_checker.register_check(CPUHealthCheck())
default_health_checker.register_check(ProcessHealthCheck())


# ============================================================================
# 便捷函数
# ============================================================================

async def check_health(check_name: Optional[str] = None) -> Dict[str, Any]:
    """
    执行健康检查（使用默认检查器）

    Args:
        check_name: 检查项名称

    Returns:
        检查结果
    """
    return await default_health_checker.check_health(check_name)


async def check_liveness() -> Dict[str, Any]:
    """
    存活检查（使用默认检查器）

    Returns:
        存活状态
    """
    return await default_health_checker.check_liveness()


async def check_readiness() -> Dict[str, Any]:
    """
    就绪检查（使用默认检查器）

    Returns:
        就绪状态
    """
    return await default_health_checker.check_readiness()


def get_health_stats() -> Dict[str, Any]:
    """
    获取健康统计（使用默认检查器）

    Returns:
        统计信息
    """
    return default_health_checker.get_stats()
