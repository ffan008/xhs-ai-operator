"""
健康检查模块单元测试
"""

import pytest
import asyncio
import time
import os
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# 添加父目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.health_check import (
    HealthStatus,
    CheckResult,
    HealthCheck,
    DiskSpaceHealthCheck,
    MemoryHealthCheck,
    CPUHealthCheck,
    ProcessHealthCheck,
    DatabaseHealthCheck,
    APIHealthCheck,
    CustomHealthCheck,
    HealthChecker,
    default_health_checker,
    check_health,
    check_liveness,
    check_readiness,
    get_health_stats
)


# ============================================================================
# 健康状态测试
# ============================================================================

class TestHealthStatus:
    """测试健康状态"""

    def test_status_values(self):
        """测试状态值"""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.UNKNOWN == "unknown"
        print("✅ 状态值正确")


# ============================================================================
# 检查结果测试
# ============================================================================

class TestCheckResult:
    """测试检查结果"""

    def test_create_result(self):
        """测试创建结果"""
        result = CheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="测试通过"
        )

        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "测试通过"
        assert result.critical is False
        print("✅ 创建结果成功")

    def test_to_dict(self):
        """测试转字典"""
        result = CheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="测试通过",
            details={"key": "value"},
            duration_ms=100.5,
            critical=True
        )

        dict_data = result.to_dict()

        assert dict_data["name"] == "test_check"
        assert dict_data["status"] == "healthy"
        assert dict_data["message"] == "测试通过"
        assert dict_data["details"] == {"key": "value"}
        assert dict_data["duration_ms"] == 100.5
        assert dict_data["critical"] is True
        print("✅ 转字典正确")


# ============================================================================
# 磁盘空间检查测试
# ============================================================================

class TestDiskSpaceHealthCheck:
    """测试磁盘空间检查"""

    @pytest.mark.asyncio
    async def test_check_disk_space(self):
        """测试检查磁盘空间"""
        check = DiskSpaceHealthCheck(
            path="/",
            warning_threshold=80.0,
            critical_threshold=90.0
        )

        result = await check.check()

        assert result.name == "disk_space"
        assert result.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY
        ]
        assert "percent_used" in result.details
        assert "gb_free" in result.details
        assert result.duration_ms >= 0
        print(f"✅ 磁盘空间检查正确: {result.message}")

    @pytest.mark.asyncio
    async def test_check_invalid_path(self):
        """测试检查无效路径"""
        check = DiskSpaceHealthCheck(
            path="/invalid/path/that/does/not/exist"
        )

        result = await check.check()

        assert result.name == "disk_space"
        assert result.status == HealthStatus.UNKNOWN
        assert "检查失败" in result.message
        print("✅ 无效路径处理正确")

    def test_history(self):
        """测试历史记录"""
        check = DiskSpaceHealthCheck()

        # 运行几次检查
        asyncio.run(check.check())
        asyncio.run(check.check())

        history = check.get_history(limit=2)

        assert len(history) <= 2
        print("✅ 历史记录正确")


# ============================================================================
# 内存检查测试
# ============================================================================

class TestMemoryHealthCheck:
    """测试内存检查"""

    @pytest.mark.asyncio
    async def test_check_memory(self):
        """测试检查内存"""
        check = MemoryHealthCheck(
            warning_threshold=80.0,
            critical_threshold=90.0
        )

        result = await check.check()

        assert result.name == "memory"
        assert result.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY
        ]
        assert "percent_used" in result.details
        assert "gb_available" in result.details
        print(f"✅ 内存检查正确: {result.message}")


# ============================================================================
# CPU 检查测试
# ============================================================================

class TestCPUHealthCheck:
    """测试 CPU 检查"""

    @pytest.mark.asyncio
    async def test_check_cpu(self):
        """测试检查 CPU"""
        check = CPUHealthCheck(
            warning_threshold=70.0,
            critical_threshold=90.0,
            interval=0.1  # 短间隔用于测试
        )

        result = await check.check()

        assert result.name == "cpu"
        assert result.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY
        ]
        assert "percent_used" in result.details
        assert "cpu_count" in result.details
        print(f"✅ CPU 检查正确: {result.message}")


# ============================================================================
# 进程检查测试
# ============================================================================

class TestProcessHealthCheck:
    """测试进程检查"""

    @pytest.mark.asyncio
    async def test_check_current_process(self):
        """测试检查当前进程"""
        check = ProcessHealthCheck()  # 默认检查当前进程

        result = await check.check()

        assert result.name == "process"
        assert result.status == HealthStatus.HEALTHY
        assert "pid" in result.details
        assert result.details["pid"] == os.getpid()
        print(f"✅ 进程检查正确: {result.message}")

    @pytest.mark.asyncio
    async def test_check_invalid_pid(self):
        """测试检查无效 PID"""
        check = ProcessHealthCheck(pid=999999999)

        result = await check.check()

        assert result.name == "process"
        assert result.status == HealthStatus.UNHEALTHY
        assert "不存在" in result.message
        print("✅ 无效 PID 处理正确")


# ============================================================================
# 数据库检查测试
# ============================================================================

class TestDatabaseHealthCheck:
    """测试数据库检查"""

    @pytest.mark.asyncio
    async def test_check_database(self):
        """测试检查数据库"""
        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            # 创建数据库表
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.commit()
            conn.close()

            # 检查数据库
            check = DatabaseHealthCheck(db_path=db_path)
            result = await check.check()

            assert result.name == "database"
            assert result.status == HealthStatus.HEALTHY
            assert "db_size_mb" in result.details
            print(f"✅ 数据库检查正确: {result.message}")

        finally:
            # 清理
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_check_nonexistent_database(self):
        """测试检查不存在的数据库"""
        check = DatabaseHealthCheck(db_path="/nonexistent/path/test.db")

        result = await check.check()

        assert result.name == "database"
        assert result.status == HealthStatus.UNHEALTHY
        assert "不存在" in result.message
        print("✅ 不存在的数据库处理正确")


# ============================================================================
# 自定义检查测试
# ============================================================================

class TestCustomHealthCheck:
    """测试自定义检查"""

    @pytest.mark.asyncio
    async def test_custom_check(self):
        """测试自定义检查"""
        def custom_check_func() -> CheckResult:
            return CheckResult(
                name="custom",
                status=HealthStatus.HEALTHY,
                message="自定义检查通过"
            )

        check = CustomHealthCheck(
            name="custom_check",
            check_func=custom_check_func
        )

        result = await check.check()

        assert result.name == "custom"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "自定义检查通过"
        print("✅ 自定义检查正确")

    @pytest.mark.asyncio
    async def test_custom_check_exception(self):
        """测试自定义检查异常"""
        def failing_check_func() -> CheckResult:
            raise ValueError("检查失败")

        check = CustomHealthCheck(
            name="failing_check",
            check_func=failing_check_func
        )

        result = await check.check()

        assert result.name == "failing_check"
        assert result.status == HealthStatus.UNKNOWN
        assert "检查失败" in result.message
        print("✅ 异常处理正确")


# ============================================================================
# 健康检查器测试
# ============================================================================

class TestHealthChecker:
    """测试健康检查器"""

    def test_initialization(self):
        """测试初始化"""
        checker = HealthChecker("test_service")

        assert checker.service_name == "test_service"
        assert len(checker._checks) == 0
        print("✅ 检查器初始化正确")

    def test_register_check(self):
        """测试注册检查"""
        checker = HealthChecker("test_service")
        check = DiskSpaceHealthCheck()

        checker.register_check(check)

        assert "disk_space" in checker._checks
        assert checker._checks["disk_space"] == check
        print("✅ 注册检查正确")

    def test_unregister_check(self):
        """测试取消注册检查"""
        checker = HealthChecker("test_service")
        check = DiskSpaceHealthCheck()

        checker.register_check(check)
        checker.unregister_check("disk_space")

        assert "disk_space" not in checker._checks
        print("✅ 取消注册正确")

    @pytest.mark.asyncio
    async def test_check_all(self):
        """测试检查所有"""
        checker = HealthChecker("test_service")
        checker.register_check(DiskSpaceHealthCheck())
        checker.register_check(MemoryHealthCheck())

        result = await checker.check_health()

        assert "service" in result
        assert result["service"] == "test_service"
        assert "status" in result
        assert "checks" in result
        assert len(result["checks"]) == 2
        print(f"✅ 检查所有正确: {result['status']}")

    @pytest.mark.asyncio
    async def test_check_specific(self):
        """测试检查特定项"""
        checker = HealthChecker("test_service")
        checker.register_check(DiskSpaceHealthCheck())
        checker.register_check(MemoryHealthCheck())

        result = await checker.check_health("disk_space")

        assert "check" in result
        assert result["check"]["name"] == "disk_space"
        print("✅ 检查特定项正确")

    @pytest.mark.asyncio
    async def test_check_liveness(self):
        """测试存活检查"""
        checker = HealthChecker("test_service")

        result = await checker.check_liveness()

        assert result["service"] == "test_service"
        assert result["status"] == "alive"
        print("✅ 存活检查正确")

    @pytest.mark.asyncio
    async def test_check_readiness(self):
        """测试就绪检查"""
        checker = HealthChecker("test_service")
        checker.register_check(DiskSpaceHealthCheck())

        result = await checker.check_readiness()

        assert result["service"] == "test_service"
        assert result["status"] in ["ready", "not_ready"]
        print(f"✅ 就绪检查正确: {result['status']}")

    def test_get_stats(self):
        """测试获取统计"""
        checker = HealthChecker("test_service")
        checker.register_check(DiskSpaceHealthCheck())
        checker.register_check(MemoryHealthCheck(critical=False))

        stats = checker.get_stats()

        assert stats["service"] == "test_service"
        assert stats["total_checks"] == 2
        assert stats["critical_checks"] == 1
        print("✅ 统计信息正确")


# ============================================================================
# 便捷函数测试
# ============================================================================

class TestConvenienceFunctions:
    """测试便捷函数"""

    @pytest.mark.asyncio
    async def test_check_health(self):
        """测试健康检查函数"""
        result = await check_health()

        assert "service" in result
        assert "status" in result
        print("✅ 健康检查函数正确")

    @pytest.mark.asyncio
    async def test_check_liveness(self):
        """测试存活检查函数"""
        result = await check_liveness()

        assert result["status"] == "alive"
        print("✅ 存活检查函数正确")

    @pytest.mark.asyncio
    async def test_check_readiness(self):
        """测试就绪检查函数"""
        result = await check_readiness()

        assert result["status"] in ["ready", "not_ready"]
        print("✅ 就绪检查函数正确")

    def test_get_health_stats(self):
        """测试获取统计函数"""
        stats = get_health_stats()

        assert "service" in stats
        assert "total_checks" in stats
        print("✅ 获取统计函数正确")


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_health_check_workflow(self):
        """测试完整健康检查流程"""
        # 创建检查器
        checker = HealthChecker("integration_test")

        # 注册检查
        checker.register_check(DiskSpaceHealthCheck())
        checker.register_check(MemoryHealthCheck())
        checker.register_check(ProcessHealthCheck())

        # 执行健康检查
        result = await checker.check_health()

        # 验证结果
        assert result["service"] == "integration_test"
        assert len(result["checks"]) == 3
        assert result["status"] in ["healthy", "degraded", "unhealthy"]

        # 获取统计
        stats = checker.get_stats()
        assert stats["total_checks"] == 3

        # 获取历史
        history = checker.get_check_history(limit=5)
        assert len(history) > 0

        print("✅ 完整健康检查流程正确")

    @pytest.mark.asyncio
    async def test_readiness_with_critical_failure(self):
        """测试关键检查失败时的就绪状态"""
        checker = HealthChecker("readiness_test")

        # 添加一个会失败的检查
        def failing_check() -> CheckResult:
            return CheckResult(
                name="failing",
                status=HealthStatus.UNHEALTHY,
                message="检查失败",
                critical=True
            )

        checker.register_check(CustomHealthCheck(
            name="failing",
            check_func=failing_check,
            critical=True
        ))

        result = await checker.check_readiness()

        # 关键检查失败，应该未就绪
        assert result["status"] == "not_ready"
        assert "failing" in result.get("reason", "")

        print("✅ 关键检查失败处理正确")


# ============================================================================
# 运行所有测试
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行健康检查系统测试...\n")

    print("="*60)
    print("测试健康状态")
    print("="*60)
    TestHealthStatus().test_status_values()

    print("\n" + "="*60)
    print("测试检查结果")
    print("="*60)
    TestCheckResult().test_create_result()
    TestCheckResult().test_to_dict()

    print("\n" + "="*60)
    print("测试磁盘空间检查")
    print("="*60)
    asyncio.run(TestDiskSpaceHealthCheck().test_check_disk_space())
    asyncio.run(TestDiskSpaceHealthCheck().test_check_invalid_path())
    TestDiskSpaceHealthCheck().test_history()

    print("\n" + "="*60)
    print("测试内存检查")
    print("="*60)
    asyncio.run(TestMemoryHealthCheck().test_check_memory())

    print("\n" + "="*60)
    print("测试 CPU 检查")
    print("="*60)
    asyncio.run(TestCPUHealthCheck().test_check_cpu())

    print("\n" + "="*60)
    print("测试进程检查")
    print("="*60)
    asyncio.run(TestProcessHealthCheck().test_check_current_process())
    asyncio.run(TestProcessHealthCheck().test_check_invalid_pid())

    print("\n" + "="*60)
    print("测试数据库检查")
    print("="*60)
    asyncio.run(TestDatabaseHealthCheck().test_check_database())
    asyncio.run(TestDatabaseHealthCheck().test_check_nonexistent_database())

    print("\n" + "="*60)
    print("测试自定义检查")
    print("="*60)
    asyncio.run(TestCustomHealthCheck().test_custom_check())
    asyncio.run(TestCustomHealthCheck().test_custom_check_exception())

    print("\n" + "="*60)
    print("测试健康检查器")
    print("="*60)
    TestHealthChecker().test_initialization()
    TestHealthChecker().test_register_check()
    TestHealthChecker().test_unregister_check()
    asyncio.run(TestHealthChecker().test_check_all())
    asyncio.run(TestHealthChecker().test_check_specific())
    asyncio.run(TestHealthChecker().test_check_liveness())
    asyncio.run(TestHealthChecker().test_check_readiness())
    TestHealthChecker().test_get_stats()

    print("\n" + "="*60)
    print("测试便捷函数")
    print("="*60)
    asyncio.run(TestConvenienceFunctions().test_check_health())
    asyncio.run(TestConvenienceFunctions().test_check_liveness())
    asyncio.run(TestConvenienceFunctions().test_check_readiness())
    TestConvenienceFunctions().test_get_health_stats()

    print("\n" + "="*60)
    print("测试集成")
    print("="*60)
    asyncio.run(TestIntegration().test_full_health_check_workflow())
    asyncio.run(TestIntegration().test_readiness_with_critical_failure())

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
