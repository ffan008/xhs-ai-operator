"""
进度反馈模块

提供进度条、状态通知、预估时间等功能，提升用户体验。
"""

import asyncio
import time
import threading
import inspect
from typing import Optional, Dict, Any, List, Callable, Awaitable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None

from .user_errors import handle_error


# ============================================================================
# 进度状态
# ============================================================================

class ProgressStatus(str, Enum):
    """进度状态"""
    PENDING = "pending"       # 等待开始
    RUNNING = "running"       # 运行中
    PAUSED = "paused"         # 已暂停
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消


# ============================================================================
# 进度条配置
# ============================================================================

@dataclass
class ProgressBarConfig:
    """进度条配置"""
    show_bar: bool = True           # 显示进度条
    show_percentage: bool = True   # 显示百分比
    show_eta: bool = True           # 显示预估时间
    show_speed: bool = False        # 显示速度
    show_count: bool = True         # 显示计数
    bar_width: int = 40             # 进度条宽度
    use_color: bool = True          # 使用颜色
    disable_on_no_tty: bool = True  # 无终端时禁用


# ============================================================================
# 任务步骤
# ============================================================================

@dataclass
class TaskStep:
    """任务步骤"""
    name: str
    status: ProgressStatus = ProgressStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """获取步骤耗时（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


# ============================================================================
# 进度信息
# ============================================================================

@dataclass
class ProgressInfo:
    """进度信息"""
    task_id: str
    task_name: str
    total: int
    completed: int = 0
    status: ProgressStatus = ProgressStatus.PENDING
    message: str = ""
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    steps: List[TaskStep] = field(default_factory=list)
    current_step: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def percentage(self) -> float:
        """获取进度百分比"""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100

    @property
    def remaining(self) -> int:
        """获取剩余数量"""
        return max(0, self.total - self.completed)

    @property
    def elapsed_time(self) -> Optional[float]:
        """获取已用时间（秒）"""
        if self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None

    @property
    def eta(self) -> Optional[float]:
        """获取预估剩余时间（秒）"""
        if self.elapsed_time and self.completed > 0:
            rate = self.completed / self.elapsed_time
            if rate > 0:
                return self.remaining / rate
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "total": self.total,
            "completed": self.completed,
            "percentage": round(self.percentage, 2),
            "status": self.status.value,
            "message": self.message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
            "elapsed_time": round(self.elapsed_time, 2) if self.elapsed_time else None,
            "eta": round(self.eta, 2) if self.eta else None,
            "steps": [
                {
                    "name": step.name,
                    "status": step.status.value,
                    "duration": step.duration
                }
                for step in self.steps
            ],
            "current_step": self.current_step,
            "metadata": self.metadata
        }


# ============================================================================
# 进度跟踪器
# ============================================================================

class ProgressTracker:
    """进度跟踪器"""

    def __init__(
        self,
        task_id: str,
        task_name: str,
        total: int,
        config: Optional[ProgressBarConfig] = None
    ):
        """
        初始化进度跟踪器

        Args:
            task_id: 任务 ID
            task_name: 任务名称
            total: 总数量
            config: 进度条配置
        """
        self.task_id = task_id
        self.task_name = task_name
        self.config = config or ProgressBarConfig()

        # 进度信息
        self.info = ProgressInfo(
            task_id=task_id,
            task_name=task_name,
            total=total
        )

        # 回调函数
        self._on_update_callbacks: List[Callable] = []

        # 同步锁
        self._lock = threading.Lock()

        # 进度条对象（如果使用 tqdm）
        self._progress_bar = None

    def start(self) -> None:
        """开始任务"""
        with self._lock:
            self.info.status = ProgressStatus.RUNNING
            self.info.started_at = datetime.now()
            self.info.updated_at = datetime.now()
            self._notify_update()

        # 创建进度条
        if self.config.show_bar and TQDM_AVAILABLE:
            from tqdm import tqdm

            self._progress_bar = tqdm(
                total=self.info.total,
                desc=self.task_name,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}",
                ncols=self.config.bar_width + 20,
                disable=self.config.disable_on_no_tty
            )

    def update(
        self,
        increment: int = 1,
        message: str = "",
        step_name: Optional[str] = None
    ) -> None:
        """
        更新进度

        Args:
            increment: 增量
            message: 状态消息
            step_name: 当前步骤名称
        """
        with self._lock:
            self.info.completed = min(self.info.completed + increment, self.info.total)
            self.info.message = message
            self.info.updated_at = datetime.now()

            # 更新预估完成时间
            if self.info.eta is not None:
                self.info.estimated_completion = datetime.now() + timedelta(seconds=self.info.eta)

            # 更新进度条
            if self._progress_bar:
                self._progress_bar.update(increment)

            # 更新步骤
            if step_name:
                self._update_step(step_name)

            self._notify_update()

    def _update_step(self, step_name: str) -> None:
        """更新当前步骤"""
        # 查找或创建步骤
        step = None
        for s in self.info.steps:
            if s.name == step_name:
                step = s
                break

        if step is None:
            step = TaskStep(name=step_name)
            self.info.steps.append(step)

        # 更新步骤状态
        if step.status == ProgressStatus.PENDING:
            step.status = ProgressStatus.RUNNING
            step.started_at = datetime.now()

    def complete_step(self, step_name: str) -> None:
        """完成步骤"""
        with self._lock:
            for step in self.info.steps:
                if step.name == step_name:
                    step.status = ProgressStatus.COMPLETED
                    step.completed_at = datetime.now()
                    break

            self.info.current_step += 1

    def set_message(self, message: str) -> None:
        """设置状态消息"""
        with self._lock:
            self.info.message = message
            self.info.updated_at = datetime.now()
            self._notify_update()

    def complete(self) -> None:
        """完成任务"""
        with self._lock:
            self.info.status = ProgressStatus.COMPLETED
            self.info.completed = self.info.total
            self.info.updated_at = datetime.now()
            self.info.estimated_completion = datetime.now()

            # 关闭进度条
            if self._progress_bar:
                self._progress_bar.close()
                self._progress_bar = None

            self._notify_update()

    def fail(self, error: str) -> None:
        """标记失败"""
        with self._lock:
            self.info.status = ProgressStatus.FAILED
            self.info.message = error
            self.info.updated_at = datetime.now()

            # 关闭进度条
            if self._progress_bar:
                self._progress_bar.close()
                self._progress_bar = None

            self._notify_update()

    def cancel(self) -> None:
        """取消任务"""
        with self._lock:
            self.info.status = ProgressStatus.CANCELLED
            self.info.updated_at = datetime.now()

            # 关闭进度条
            if self._progress_bar:
                self._progress_bar.close()
                self._progress_bar = None

            self._notify_update()

    def pause(self) -> None:
        """暂停任务"""
        with self._lock:
            self.info.status = ProgressStatus.PAUSED
            self.info.updated_at = datetime.now()
            self._notify_update()

    def resume(self) -> None:
        """恢复任务"""
        with self._lock:
            self.info.status = ProgressStatus.RUNNING
            self.info.updated_at = datetime.now()
            self._notify_update()

    def add_step(self, step_name: str) -> None:
        """添加步骤"""
        with self._lock:
            step = TaskStep(name=step_name)
            self.info.steps.append(step)

    def on_update(self, callback: Callable[[ProgressInfo], None]) -> None:
        """
        注册更新回调

        Args:
            callback: 回调函数
        """
        self._on_update_callbacks.append(callback)

    def _notify_update(self) -> None:
        """通知更新"""
        for callback in self._on_update_callbacks:
            try:
                callback(self.info)
            except Exception:
                pass

    def get_progress(self) -> ProgressInfo:
        """获取当前进度"""
        with self._lock:
            # 返回副本
            return self.info

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "task_id": self.task_id,
                "task_name": self.task_name,
                "percentage": self.info.percentage,
                "elapsed_time": self.info.elapsed_time,
                "eta": self.info.eta,
                "status": self.info.status.value
            }


# ============================================================================
# 进度管理器
# ============================================================================

class ProgressManager:
    """进度管理器"""

    def __init__(self):
        """初始化进度管理器"""
        self._trackers: Dict[str, ProgressTracker] = {}
        self._lock = threading.Lock()

    def create_tracker(
        self,
        task_id: str,
        task_name: str,
        total: int,
        config: Optional[ProgressBarConfig] = None
    ) -> ProgressTracker:
        """
        创建进度跟踪器

        Args:
            task_id: 任务 ID
            task_name: 任务名称
            total: 总数量
            config: 进度条配置

        Returns:
            进度跟踪器
        """
        tracker = ProgressTracker(task_id, task_name, total, config)

        with self._lock:
            self._trackers[task_id] = tracker

        return tracker

    def get_tracker(self, task_id: str) -> Optional[ProgressTracker]:
        """
        获取进度跟踪器

        Args:
            task_id: 任务 ID

        Returns:
            进度跟踪器（如果存在）
        """
        return self._trackers.get(task_id)

    def remove_tracker(self, task_id: str) -> None:
        """
        移除进度跟踪器

        Args:
            task_id: 任务 ID
        """
        with self._lock:
            if task_id in self._trackers:
                del self._trackers[task_id]

    def get_all_progress(self) -> List[ProgressInfo]:
        """获取所有任务的进度"""
        with self._lock:
            return [tracker.get_progress() for tracker in self._trackers.values()]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_tasks": len(self._trackers),
                "running_tasks": sum(
                    1 for t in self._trackers.values()
                    if t.info.status == ProgressStatus.RUNNING
                ),
                "completed_tasks": sum(
                    1 for t in self._trackers.values()
                    if t.info.status == ProgressStatus.COMPLETED
                ),
                "failed_tasks": sum(
                    1 for t in self._trackers.values()
                    if t.info.status == ProgressStatus.FAILED
                )
            }


# ============================================================================
# 异步进度装饰器
# ============================================================================

def track_progress(
    task_name: Optional[str] = None,
    total: Optional[int] = None,
    config: Optional[ProgressBarConfig] = None
):
    """
    跟踪进度的装饰器

    Args:
        task_name: 任务名称
        total: 总数量
        config: 进度条配置

    Returns:
        装饰器函数

    示例:
        @track_progress("处理文件", total=100)
        def process_files(files):
            for i, file in enumerate(files):
                process(file)
                # 自动更新进度
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 生成任务 ID
            task_id = f"{func.__name__}_{id(func)}"

            # 确定总数量
            actual_total = total
            if actual_total is None:
                # 尝试从参数中推断
                if args and hasattr(args[0], '__len__'):
                    actual_total = len(args[0])

            if actual_total is None:
                # 无法推断，不跟踪进度
                return func(*args, **kwargs)

            # 创建跟踪器
            actual_task_name = task_name or func.__name__
            tracker = default_progress_manager.create_tracker(
                task_id, actual_task_name, actual_total, config
            )

            # 启动
            tracker.start()

            try:
                # 执行函数
                result = func(*args, **kwargs)

                # 如果是迭代器，包装以更新进度
                # 优先检查生成器（因为 asyncio.iscoroutine 也会返回 True 给生成器）
                if inspect.isgenerator(result):
                    # 同步生成器
                    return _SyncProgressIterator(tracker, result)
                elif asyncio.iscoroutinefunction(func) or asyncio.iscoroutine(result):
                    # 异步函数
                    return _AsyncProgressIterator(tracker, result)
                elif hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                    # 同步迭代器（排除字符串和字节）
                    return _SyncProgressIterator(tracker, result)
                else:
                    tracker.complete()
                    return result

            except Exception as e:
                tracker.fail(str(e))
                raise

        return wrapper
    return decorator


class _SyncProgressIterator:
    """同步进度迭代器"""

    def __init__(self, tracker: ProgressTracker, iterable):
        self.tracker = tracker
        self.iterator = iter(iterable)  # 将可迭代对象转换为迭代器

    def __iter__(self):
        return self

    def __next__(self):
        try:
            item = next(self.iterator)
            self.tracker.update(1)
            return item
        except StopIteration:
            self.tracker.complete()
            raise


class _AsyncProgressIterator:
    """异步进度迭代器"""

    def __init__(self, tracker: ProgressTracker, async_iterator):
        self.tracker = tracker
        self.async_iterator = async_iterator

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            item = await self.async_iterator.__anext__()
            self.tracker.update(1)
            return item
        except StopAsyncIteration:
            self.tracker.complete()
            raise


# ============================================================================
# 进度通知器
# ============================================================================

class ProgressNotifier:
    """进度通知器"""

    def __init__(self):
        """初始化通知器"""
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(
        self,
        task_id: str,
        callback: Callable[[ProgressInfo], None]
    ) -> None:
        """
        订阅进度更新

        Args:
            task_id: 任务 ID
            callback: 回调函数
        """
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []

        self._subscribers[task_id].append(callback)

    def unsubscribe(
        self,
        task_id: str,
        callback: Callable[[ProgressInfo], None]
    ) -> None:
        """
        取消订阅

        Args:
            task_id: 任务 ID
            callback: 回调函数
        """
        if task_id in self._subscribers:
            if callback in self._subscribers[task_id]:
                self._subscribers[task_id].remove(callback)

    def notify(self, progress_info: ProgressInfo) -> None:
        """
        通知所有订阅者

        Args:
            progress_info: 进度信息
        """
        task_id = progress_info.task_id

        if task_id in self._subscribers:
            for callback in self._subscribers[task_id]:
                try:
                    callback(progress_info)
                except Exception:
                    pass


# ============================================================================
# 状态通知器
# ============================================================================

class StatusNotification:
    """状态通知"""

    def __init__(self, progress_info: ProgressInfo):
        """初始化状态通知"""
        self.progress_info = progress_info

    def get_status_message(self) -> str:
        """获取状态消息"""
        p = self.progress_info

        if p.status == ProgressStatus.RUNNING:
            if p.message:
                return f"🔄 {p.message} ({p.percentage:.1f}%)"
            else:
                return f"🔄 进行中... ({p.percentage:.1f}%)"

        elif p.status == ProgressStatus.COMPLETED:
            return f"✅ {p.task_name} 已完成"

        elif p.status == ProgressStatus.FAILED:
            return f"❌ {p.task_name} 失败: {p.message}"

        elif p.status == ProgressStatus.PAUSED:
            return f"⏸️ {p.task_name} 已暂停"

        elif p.status == ProgressStatus.CANCELLED:
            return f"🚫 {p.task_name} 已取消"

        else:
            return f"⏳ {p.task_name} 等待开始..."

    def get_detailed_message(self) -> str:
        """获取详细消息"""
        p = self.progress_info
        lines = []

        lines.append(f"任务: {p.task_name}")
        lines.append(f"状态: {p.status.value}")
        lines.append(f"进度: {p.completed}/{p.total} ({p.percentage:.1f}%)")

        if p.message:
            lines.append(f"消息: {p.message}")

        if p.elapsed_time:
            lines.append(f"已用时间: {self._format_time(p.elapsed_time)}")

        if p.eta:
            lines.append(f"预估剩余: {self._format_time(p.eta)}")

        if p.steps:
            lines.append("\n步骤:")
            for i, step in enumerate(p.steps, 1):
                status_icon = {
                    ProgressStatus.PENDING: "⏳",
                    ProgressStatus.RUNNING: "🔄",
                    ProgressStatus.COMPLETED: "✅",
                    ProgressStatus.FAILED: "❌"
                }.get(step.status, "⏸️")
                duration = f" ({self._format_time(step.duration)})" if step.duration else ""
                lines.append(f"  {i}. {status_icon} {step.name}{duration}")

        return "\n".join(lines)

    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}分{secs}秒"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}小时{minutes}分"


# ============================================================================
# 全局实例
# ============================================================================

# 默认进度管理器
default_progress_manager = ProgressManager()

# 默认通知器
default_notifier = ProgressNotifier()


# ============================================================================
# 便捷函数
# ============================================================================

def create_progress(
    task_id: str,
    task_name: str,
    total: int
) -> ProgressTracker:
    """
    创建进度跟踪器（使用默认管理器）

    Args:
        task_id: 任务 ID
        task_name: 任务名称
        total: 总数量

    Returns:
        进度跟踪器
    """
    return default_progress_manager.create_tracker(task_id, task_name, total)


def get_progress(task_id: str) -> Optional[ProgressInfo]:
    """
    获取任务进度（使用默认管理器）

    Args:
        task_id: 任务 ID

    Returns:
        进度信息（如果存在）
    """
    tracker = default_progress_manager.get_tracker(task_id)
    if tracker:
        return tracker.get_progress()
    return None


def format_progress(progress_info: ProgressInfo) -> str:
    """
    格式化进度信息（使用默认通知器）

    Args:
        progress_info: 进度信息

    Returns:
        格式化的文本
    """
    notification = StatusNotification(progress_info)
    return notification.get_status_message()
