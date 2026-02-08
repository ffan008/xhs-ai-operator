"""
分布式调度器的单元测试（简化版）
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# 添加父目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.scheduler import (
    TaskStatus,
    ScheduledTask,
    TaskExecutor,
    DistributedScheduler
)


# ============================================================================
# ScheduledTask 测试
# ============================================================================

class TestScheduledTask:
    """测试定时任务"""

    def test_create_task(self):
        """测试创建任务"""
        task = ScheduledTask(
            id="task1",
            name="测试任务",
            cron_expression="0 9 * * *",
            workflow_config={"workflow": "test"},
            enabled=True
        )

        assert task.id == "task1"
        assert task.name == "测试任务"
        assert task.enabled == True
        print("✅ 任务创建成功")

    def test_to_dict(self):
        """测试转换为字典"""
        task = ScheduledTask(
            id="task1",
            name="测试任务",
            cron_expression="0 9 * * *",
            workflow_config={"workflow": "test"}
        )

        task_dict = task.to_dict()

        assert task_dict["id"] == "task1"
        assert task_dict["name"] == "测试任务"
        print("✅ 转字典成功")

    def test_from_dict(self):
        """测试从字典创建"""
        task_dict = {
            "id": "task1",
            "name": "测试任务",
            "cron_expression": "0 9 * * *",
            "workflow_config": {"workflow": "test"},
            "enabled": True
        }

        task = ScheduledTask.from_dict(task_dict)

        assert task.id == "task1"
        assert task.name == "测试任务"
        print("✅ 从字典创建成功")


# ============================================================================
# TaskExecutor 测试
# ============================================================================

class TestTaskExecutor:
    """测试任务执行器"""

    @pytest.mark.asyncio
    async def test_execute_task_success(self):
        """测试成功执行任务"""
        executor = TaskExecutor(instance_id="test_instance")

        task = ScheduledTask(
            id="task1",
            name="测试任务",
            cron_expression="0 9 * * *",
            workflow_config={"workflow": "test"}
        )

        async def mock_workflow(config):
            await asyncio.sleep(0.01)
            return {"result": "success"}

        result = await executor.execute_task(task, mock_workflow)

        assert result["task_id"] == "task1"
        assert result["status"] == TaskStatus.SUCCESS
        assert result["output"]["result"] == "success"
        print("✅ 任务执行成功")

    @pytest.mark.asyncio
    async def test_execute_task_failure(self):
        """测试任务执行失败"""
        executor = TaskExecutor(instance_id="test_instance")

        task = ScheduledTask(
            id="task1",
            name="测试任务",
            cron_expression="0 9 * * *",
            workflow_config={"workflow": "test"}
        )

        async def mock_workflow(config):
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        result = await executor.execute_task(task, mock_workflow)

        assert result["status"] == TaskStatus.FAILED
        assert "error" in result
        print("✅ 任务失败处理正确")

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """测试并发执行"""
        executor = TaskExecutor(max_concurrent=2)

        tasks = []
        for i in range(3):
            task = ScheduledTask(
                id=f"task{i}",
                name=f"任务{i}",
                cron_expression="0 9 * * *",
                workflow_config={"index": i}
            )
            tasks.append(task)

        execution_count = 0

        async def mock_workflow(config):
            nonlocal execution_count
            execution_count += 1
            await asyncio.sleep(0.1)
            return config

        # 并发执行所有任务
        results = await asyncio.gather(*[
            executor.execute_task(task, mock_workflow)
            for task in tasks
        ])

        assert execution_count == 3
        assert len(results) == 3
        print("✅ 并发执行成功")


# ============================================================================
# DistributedScheduler 测试
# ============================================================================

class TestDistributedScheduler:
    """测试分布式调度器"""

    @pytest.mark.asyncio
    async def test_scheduler_stats(self):
        """测试调度器统计"""
        scheduler = DistributedScheduler()

        stats = scheduler.get_stats()

        assert "running" in stats
        assert "executor_stats" in stats
        assert "registered_workflows" in stats
        print("✅ 调度器统计成功")

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """测试启动和停止调度器"""
        from unittest.mock import AsyncMock, patch

        scheduler = DistributedScheduler(tick_interval=0.1)

        # Mock Redis 连接相关方法
        async def mock_connect():
            pass

        def mock_is_connected():
            return True

        scheduler.redis_cache.connect = mock_connect
        scheduler.redis_cache.is_connected = mock_is_connected

        # 启动调度器
        await scheduler.start()
        assert scheduler._running is True

        # 等待一小段时间
        await asyncio.sleep(0.2)

        # 停止调度器
        await scheduler.stop()
        assert scheduler._running is False
        print("✅ 启动和停止调度器成功")


# ============================================================================
# 并发测试
# ============================================================================

class TestConcurrency:
    """测试并发特性"""

    @pytest.mark.asyncio
    async def test_instance_id_unique(self):
        """测试实例 ID 唯一性"""
        executor1 = TaskExecutor()
        executor2 = TaskExecutor()

        assert executor1.instance_id != executor2.instance_id
        print("✅ 实例 ID 唯一")

    @pytest.mark.asyncio
    async def test_concurrent_limit(self):
        """测试并发限制"""
        executor = TaskExecutor(max_concurrent=2)

        running_count = 0
        max_running = 0

        async def mock_workflow(config):
            nonlocal running_count, max_running
            running_count += 1
            max_running = max(max_running, running_count)
            await asyncio.sleep(0.1)
            running_count -= 1
            return {"result": "success"}

        # 创建 5 个任务
        tasks = []
        for i in range(5):
            task = ScheduledTask(
                id=f"task{i}",
                name=f"任务{i}",
                cron_expression="0 9 * * *",
                workflow_config={"index": i}
            )
            tasks.append(executor.execute_task(task, mock_workflow))

        # 并发执行
        await asyncio.gather(*tasks)

        # 验证最大并发数
        assert max_running <= 2
        print("✅ 并发限制正常")


def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行调度器优化测试...\n")

    print("="*60)
    print("测试定时任务")
    print("="*60)
    TestScheduledTask().test_create_task()
    TestScheduledTask().test_to_dict()
    TestScheduledTask().test_from_dict()

    print("\n" + "="*60)
    print("测试任务执行器")
    print("="*60)
    asyncio.run(TestTaskExecutor().test_execute_task_success())
    asyncio.run(TestTaskExecutor().test_execute_task_failure())
    asyncio.run(TestTaskExecutor().test_concurrent_execution())

    print("\n" + "="*60)
    print("测试分布式调度器")
    print("="*60)
    asyncio.run(TestDistributedScheduler().test_scheduler_stats())
    asyncio.run(TestDistributedScheduler().test_start_stop())

    print("\n" + "="*60)
    print("测试并发特性")
    print("="*60)
    asyncio.run(TestConcurrency().test_instance_id_unique())
    asyncio.run(TestConcurrency().test_concurrent_limit())

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
