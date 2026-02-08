"""
进度反馈模块单元测试
"""

import pytest
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from threading import Thread

# 添加父目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.progress import (
    ProgressStatus,
    ProgressBarConfig,
    TaskStep,
    ProgressInfo,
    ProgressTracker,
    ProgressManager,
    ProgressNotifier,
    StatusNotification,
    track_progress,
    default_progress_manager,
    create_progress,
    get_progress,
    format_progress
)


# ============================================================================
# 进度状态测试
# ============================================================================

class TestProgressStatus:
    """测试进度状态"""

    def test_status_values(self):
        """测试状态值"""
        assert ProgressStatus.PENDING == "pending"
        assert ProgressStatus.RUNNING == "running"
        assert ProgressStatus.PAUSED == "paused"
        assert ProgressStatus.COMPLETED == "completed"
        assert ProgressStatus.FAILED == "failed"
        assert ProgressStatus.CANCELLED == "cancelled"
        print("✅ 状态值正确")


# ============================================================================
# 进度信息测试
# ============================================================================

class TestProgressInfo:
    """测试进度信息"""

    def test_initialization(self):
        """测试初始化"""
        info = ProgressInfo(
            task_id="task1",
            task_name="测试任务",
            total=100
        )

        assert info.task_id == "task1"
        assert info.task_name == "测试任务"
        assert info.total == 100
        assert info.completed == 0
        assert info.status == ProgressStatus.PENDING
        print("✅ 初始化正确")

    def test_percentage(self):
        """测试百分比计算"""
        info = ProgressInfo(
            task_id="task1",
            task_name="测试",
            total=100
        )

        assert info.percentage == 0.0

        info.completed = 50
        assert info.percentage == 50.0

        info.completed = 100
        assert info.percentage == 100.0

        # 测试除零保护
        info_zero = ProgressInfo(task_id="task2", task_name="测试", total=0)
        assert info_zero.percentage == 0.0

        print("✅ 百分比计算正确")

    def test_remaining(self):
        """测试剩余数量"""
        info = ProgressInfo(
            task_id="task1",
            task_name="测试",
            total=100
        )

        assert info.remaining == 100

        info.completed = 30
        assert info.remaining == 70

        info.completed = 100
        assert info.remaining == 0

        # 超过总数的情况
        info.completed = 150
        assert info.remaining == 0

        print("✅ 剩余数量正确")

    def test_elapsed_time(self):
        """测试已用时间"""
        info = ProgressInfo(
            task_id="task1",
            task_name="测试",
            total=100
        )

        # 没有开始时间
        assert info.elapsed_time is None

        # 有开始时间
        info.started_at = datetime.now()
        time.sleep(0.1)

        elapsed = info.elapsed_time
        assert elapsed is not None
        assert elapsed >= 0.1

        print("✅ 已用时间正确")

    def test_eta(self):
        """测试预估时间"""
        info = ProgressInfo(
            task_id="task1",
            task_name="测试",
            total=100
        )

        info.started_at = datetime.now()
        info.completed = 50

        time.sleep(0.1)

        # 计算 ETA
        eta = info.eta
        assert eta is not None
        assert eta > 0  # 应该大于 0

        print("✅ 预估时间正确")

    def test_to_dict(self):
        """测试转换为字典"""
        info = ProgressInfo(
            task_id="task1",
            task_name="测试任务",
            total=100,
            completed=50,
            status=ProgressStatus.RUNNING
        )

        info.started_at = datetime.now()

        dict_data = info.to_dict()

        assert dict_data["task_id"] == "task1"
        assert dict_data["percentage"] == 50.0
        assert dict_data["status"] == "running"
        assert "started_at" in dict_data

        print("✅ 转字典正确")


# ============================================================================
# 任务步骤测试
# ============================================================================

class TestTaskStep:
    """测试任务步骤"""

    def test_create_step(self):
        """测试创建步骤"""
        step = TaskStep(
            name="步骤1",
            status=ProgressStatus.RUNNING,
            started_at=datetime.now()  # 手动设置开始时间
        )

        assert step.name == "步骤1"
        assert step.status == ProgressStatus.RUNNING
        assert step.started_at is not None
        print("✅ 创建步骤成功")

    def test_step_duration(self):
        """测试步骤耗时"""
        step = TaskStep(name="步骤1")

        assert step.duration is None

        step.started_at = datetime.now()
        time.sleep(0.05)
        step.completed_at = datetime.now()

        duration = step.duration
        assert duration is not None
        assert duration >= 0.05

        print("✅ 步骤耗时正确")


# ============================================================================
# 进度跟踪器测试
# ============================================================================

class TestProgressTracker:
    """测试进度跟踪器"""

    def test_initialization(self):
        """测试初始化"""
        tracker = ProgressTracker(
            task_id="task1",
            task_name="测试任务",
            total=100
        )

        assert tracker.task_id == "task1"
        assert tracker.info.total == 100
        assert tracker.info.status == ProgressStatus.PENDING

        print("✅ 跟踪器初始化正确")

    def test_start(self):
        """测试开始"""
        tracker = ProgressTracker(
            task_id="task1",
            task_name="测试",
            total=100
        )

        tracker.start()

        assert tracker.info.status == ProgressStatus.RUNNING
        assert tracker.info.started_at is not None

        print("✅ 开始任务正确")

    def test_update(self):
        """测试更新"""
        tracker = ProgressTracker(
            task_id="task1",
            task_name="测试",
            total=100
        )

        tracker.start()

        tracker.update(10)
        assert tracker.info.completed == 10
        assert tracker.info.percentage == 10.0

        tracker.update(20)
        assert tracker.info.completed == 30
        assert tracker.info.percentage == 30.0

        print("✅ 更新进度正确")

    def test_set_message(self):
        """测试设置消息"""
        tracker = ProgressTracker(
            task_id="task1",
            task_name="测试",
            total=100
        )

        tracker.set_message("处理中...")
        assert tracker.info.message == "处理中..."

        print("✅ 设置消息正确")

    def test_complete(self):
        """测试完成"""
        tracker = ProgressTracker(
            task_id="task1",
            task_name="测试",
            total=100
        )

        tracker.start()
        tracker.update(50)

        tracker.complete()

        assert tracker.info.status == ProgressStatus.COMPLETED
        assert tracker.info.completed == 100
        assert tracker.info.estimated_completion is not None

        print("✅ 完成任务正确")

    def test_fail(self):
        """测试失败"""
        tracker = ProgressTracker(
            task_id="task1",
            task_name="测试",
            total=100
        )

        tracker.start()

        tracker.fail("发生错误")

        assert tracker.info.status == ProgressStatus.FAILED
        assert tracker.info.message == "发生错误"

        print("✅ 失败处理正确")

    def test_cancel(self):
        """测试取消"""
        tracker = ProgressTracker(
            task_id="task1",
            task_name="测试",
            total=100
        )

        tracker.start()
        tracker.cancel()

        assert tracker.info.status == ProgressStatus.CANCELLED

        print("✅ 取消任务正确")

    def test_pause_resume(self):
        """测试暂停和恢复"""
        tracker = ProgressTracker(
            task_id="task1",
            task_name="测试",
            total=100
        )

        tracker.start()
        tracker.update(10)

        tracker.pause()
        assert tracker.info.status == ProgressStatus.PAUSED

        tracker.resume()
        assert tracker.info.status == ProgressStatus.RUNNING

        print("✅ 暂停和恢复正确")

    def test_steps(self):
        """测试步骤"""
        tracker = ProgressTracker(
            task_id="task1",
            task_name="测试",
            total=100
        )

        tracker.add_step("步骤1")
        tracker.add_step("步骤2")

        assert len(tracker.info.steps) == 2

        # 完成第一步
        tracker.complete_step("步骤1")
        assert tracker.info.current_step == 1

        print("✅ 步骤管理正确")

    def test_callback(self):
        """测试回调"""
        tracker = ProgressTracker(
            task_id="task1",
            task_name="测试",
            total=100
        )

        callback_called = []

        def callback(progress_info):
            callback_called.append(progress_info)

        tracker.on_update(callback)

        tracker.start()
        tracker.update(10)

        assert len(callback_called) > 0

        print("✅ 回调功能正确")


# ============================================================================
# 进度管理器测试
# ============================================================================

class TestProgressManager:
    """测试进度管理器"""

    def test_initialization(self):
        """测试初始化"""
        manager = ProgressManager()

        assert manager._trackers == {}
        print("✅ 管理器初始化正确")

    def test_create_tracker(self):
        """测试创建跟踪器"""
        manager = ProgressManager()

        tracker = manager.create_tracker(
            task_id="task1",
            task_name="测试",
            total=100
        )

        assert tracker is not None
        assert manager.get_tracker("task1") == tracker

        print("✅ 创建跟踪器正确")

    def test_get_tracker(self):
        """测试获取跟踪器"""
        manager = ProgressManager()

        tracker = manager.create_tracker("task1", "测试", 100)
        retrieved = manager.get_tracker("task1")

        assert retrieved is not None
        assert retrieved.task_id == "task1"

        # 获取不存在的
        none_retrieved = manager.get_tracker("nonexistent")
        assert none_retrieved is None

        print("✅ 获取跟踪器正确")

    def test_remove_tracker(self):
        """测试移除跟踪器"""
        manager = ProgressManager()

        manager.create_tracker("task1", "测试", 100)
        assert manager.get_tracker("task1") is not None

        manager.remove_tracker("task1")
        assert manager.get_tracker("task1") is None

        print("✅ 移除跟踪器正确")

    def test_get_all_progress(self):
        """测试获取所有进度"""
        manager = ProgressManager()

        # 创建多个跟踪器
        manager.create_tracker("task1", "任务1", 100)
        manager.create_tracker("task2", "任务2", 50)

        all_progress = manager.get_all_progress()

        assert len(all_progress) == 2
        task_ids = {p.task_id for p in all_progress}
        assert "task1" in task_ids
        assert "task2" in task_ids

        print("✅ 获取所有进度正确")

    def test_get_stats(self):
        """测试获取统计"""
        manager = ProgressManager()

        # 创建跟踪器并设置状态
        tracker1 = manager.create_tracker("task1", "任务1", 100)
        tracker1.start()
        tracker1.update(50)

        tracker2 = manager.create_tracker("task2", "任务2", 100)
        tracker2.start()
        tracker2.complete()

        stats = manager.get_stats()

        assert stats["total_tasks"] == 2
        assert stats["running_tasks"] == 1
        assert stats["completed_tasks"] == 1

        print("✅ 统计信息正确")


# ============================================================================
# 状态通知测试
# ============================================================================

class TestStatusNotification:
    """测试状态通知"""

    def test_running_status(self):
        """测试运行中状态"""
        info = ProgressInfo(
            task_id="task1",
            task_name="测试任务",
            total=100,
            completed=50,
            status=ProgressStatus.RUNNING,
            message="正在处理"
        )

        notification = StatusNotification(info)
        message = notification.get_status_message()

        assert "🔄" in message
        assert "50.0%" in message

        print("✅ 运行状态消息正确")

    def test_completed_status(self):
        """测试完成状态"""
        info = ProgressInfo(
            task_id="task1",
            task_name="测试任务",
            total=100,
            completed=100,
            status=ProgressStatus.COMPLETED
        )

        notification = StatusNotification(info)
        message = notification.get_status_message()

        assert "✅" in message
        assert "已完成" in message

        print("✅ 完成状态消息正确")

    def test_failed_status(self):
        """测试失败状态"""
        info = ProgressInfo(
            task_id="task1",
            task_name="测试任务",
            total=100,
            status=ProgressStatus.FAILED,
            message="连接失败"
        )

        notification = StatusNotification(info)
        message = notification.get_status_message()

        assert "❌" in message
        assert "失败" in message
        assert "连接失败" in message

        print("✅ 失败状态消息正确")

    def test_detailed_message(self):
        """测试详细消息"""
        info = ProgressInfo(
            task_id="task1",
            task_name="测试任务",
            total=100,
            completed=50,
            status=ProgressStatus.RUNNING,
            message="处理中"
        )

        info.started_at = datetime.now()
        time.sleep(0.1)

        notification = StatusNotification(info)
        detailed = notification.get_detailed_message()

        assert "任务: 测试任务" in detailed
        assert "进度: 50/100 (50.0%)" in detailed
        assert "已用时间:" in detailed
        assert "预估剩余:" in detailed

        print("✅ 详细消息正确")


# ============================================================================
# 进度装饰器测试
# ============================================================================

class TestProgressDecorator:
    """测试进度装饰器"""

    def test_decorator_basic(self):
        """测试基本装饰器"""
        @track_progress("测试任务", total=10)
        def process_items(items):
            results = []
            for item in items:
                results.append(item * 2)
            return results

        items = list(range(10))
        result = process_items(items)

        # 装饰器会返回迭代器，需要转换为列表
        result = list(result)
        assert len(result) == 10
        assert result[0] == 0
        assert result[9] == 18

        print("✅ 基本装饰器正确")

    def test_decorator_with_iterable(self):
        """测试装饰器处理迭代器"""
        @track_progress(total=100)
        def generate_numbers():
            for i in range(100):
                yield i

        result = list(generate_numbers())

        assert len(result) == 100
        assert sum(result) == 4950  # 0+1+...+99

        print("✅ 迭代器装饰器正确")

    def test_decorator_auto_infer(self):
        """测试装饰器自动推断总数"""
        @track_progress("自动推断")
        def process_list(items):
            return [x * 2 for x in items]

        items = list(range(10))
        result = process_list(items)

        # 装饰器会返回迭代器，需要转换为列表
        result = list(result)
        assert len(result) == 10

        print("✅ 自动推断总数正确")


# ============================================================================
# 便捷函数测试
# ============================================================================

class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_create_progress(self):
        """测试创建进度"""
        tracker = create_progress("task1", "测试", 100)

        assert tracker.task_id == "task1"
        assert tracker.info.total == 100

        print("✅ 创建进度正确")

    def test_get_progress(self):
        """测试获取进度"""
        tracker = create_progress("task1", "测试", 100)
        tracker.start()
        tracker.update(10)

        progress = get_progress("task1")

        assert progress is not None
        assert progress.completed == 10

        # 获取不存在的
        none_progress = get_progress("nonexistent")
        assert none_progress is None

        print("✅ 获取进度正确")

    def test_format_progress(self):
        """测试格式化进度"""
        info = ProgressInfo(
            task_id="task1",
            task_name="测试任务",
            total=100,
            completed=50,
            status=ProgressStatus.RUNNING,
            message="处理中"
        )

        formatted = format_progress(info)

        assert "🔄" in formatted
        assert "50.0%" in formatted

        print("✅ 格式化进度正确")


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        # 创建进度
        tracker = create_progress("task1", "批量处理", 100)

        # 注册回调
        updates = []
        tracker.on_update(lambda p: updates.append(p))

        # 开始
        tracker.start()
        assert len(updates) > 0

        # 更新进度
        for i in range(10):
            tracker.update(10)

        # 检查进度
        progress = tracker.get_progress()
        assert progress.percentage == 100.0

        # 完成
        tracker.complete()
        assert tracker.info.status == ProgressStatus.COMPLETED

        print("✅ 完整工作流正确")

    def test_multiple_tasks(self):
        """测试多任务管理"""
        manager = ProgressManager()

        # 创建多个任务
        tracker1 = manager.create_tracker("task1", "任务1", 50)
        tracker2 = manager.create_tracker("task2", "任务2", 100)

        tracker1.start()
        tracker1.update(25)

        tracker2.start()
        tracker2.update(50)
        tracker2.complete()

        stats = manager.get_stats()

        assert stats["total_tasks"] == 2
        assert stats["running_tasks"] == 1
        assert stats["completed_tasks"] == 1

        print("✅ 多任务管理正确")


# ============================================================================
# 运行所有测试
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行进度反馈优化测试...\n")

    print("="*60)
    print("测试进度状态")
    print("="*60)
    TestProgressStatus().test_status_values()

    print("\n" + "="*60)
    print("测试进度信息")
    print("="*60)
    TestProgressInfo().test_initialization()
    TestProgressInfo().test_percentage()
    TestProgressInfo().test_remaining()
    TestProgressInfo().test_elapsed_time()
    TestProgressInfo().test_eta()
    TestProgressInfo().test_to_dict()

    print("\n" + "="*60)
    print("测试任务步骤")
    print("="*60)
    TestTaskStep().test_create_step()
    TestTaskStep().test_step_duration()

    print("\n" + "="*60)
    print("测试进度跟踪器")
    print("="*60)
    TestProgressTracker().test_initialization()
    TestProgressTracker().test_start()
    TestProgressTracker().test_update()
    TestProgressTracker().test_set_message()
    TestProgressTracker().test_complete()
    TestProgressTracker().test_fail()
    TestProgressTracker().test_cancel()
    TestProgressTracker().test_pause_resume()
    TestProgressTracker().test_steps()
    TestProgressTracker().test_callback()

    print("\n" + "="*60)
    print("测试进度管理器")
    print("="*60)
    TestProgressManager().test_initialization()
    TestProgressManager().test_create_tracker()
    TestProgressManager().test_get_tracker()
    TestProgressManager().test_remove_tracker()
    TestProgressManager().test_get_all_progress()
    TestProgressManager().test_get_stats()

    print("\n" + "="*60)
    print("测试状态通知")
    print("="*60)
    TestStatusNotification().test_running_status()
    TestStatusNotification().test_completed_status()
    TestStatusNotification().test_failed_status()
    TestStatusNotification().test_detailed_message()

    print("\n" + "="*60)
    print("测试进度装饰器")
    print("="*60)
    TestProgressDecorator().test_decorator_basic()
    TestProgressDecorator().test_decorator_with_iterable()
    TestProgressDecorator().test_decorator_auto_infer()

    print("\n" + "="*60)
    print("测试便捷函数")
    print("="*60)
    TestConvenienceFunctions().test_create_progress()
    TestConvenienceFunctions().test_get_progress()
    TestConvenienceFunctions().test_format_progress()

    print("\n" + "="*60)
    print("测试集成")
    print("="*60)
    TestIntegration().test_full_workflow()
    TestIntegration().test_multiple_tasks()

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
