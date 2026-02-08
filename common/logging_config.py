"""
结构化日志配置模块

提供 JSON 格式结构化日志、上下文管理、日志级别等功能。
"""

import logging
import json
import sys
import os
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from contextlib import contextmanager
from functools import wraps
import traceback


# ============================================================================
# 日志级别
# ============================================================================

class LogLevel:
    """日志级别"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


# ============================================================================
# JSON 格式化器
# ============================================================================

class JSONFormatter(logging.Formatter):
    """JSON 格式化器"""

    def __init__(
        self,
        *,
        timestamp_format: str = "%Y-%m-%dT%H:%M:%S.%fZ",
        include_extra: bool = True
    ):
        """
        初始化 JSON 格式化器

        Args:
            timestamp_format: 时间戳格式
            include_extra: 是否包含额外字段
        """
        super().__init__()
        self.timestamp_format = timestamp_format
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为 JSON

        Args:
            record: 日志记录

        Returns:
            JSON 字符串
        """
        # 基础字段
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).strftime(
                self.timestamp_format
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
            "thread_name": record.threadName
        }

        # 异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }

        # 额外字段
        if self.include_extra and hasattr(record, "extra"):
            log_data.update(record.extra)

        # 自定义字段
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                'relativeCreated', 'thread', 'threadName', 'processName',
                'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info'
            }:
                log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False, default=str)


# ============================================================================
# 彩色格式化器
# ============================================================================

class ColorFormatter(logging.Formatter):
    """彩色终端格式化器"""

    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'

    def __init__(self, fmt: Optional[str] = None):
        """
        初始化彩色格式化器

        Args:
            fmt: 格式字符串
        """
        if fmt is None:
            fmt = (
                '%(asctime)s | %(levelname)-8s | %(name)s | '
                '%(filename)s:%(lineno)d | %(message)s'
            )
        super().__init__(fmt)

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录（带颜色）

        Args:
            record: 日志记录

        Returns:
            格式化字符串
        """
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        formatted = super().format(record)
        # 恢复原始 levelname（避免影响其他处理器）
        record.levelname = levelname
        return formatted


# ============================================================================
# 结构化日志记录器
# ============================================================================

class StructuredLogger:
    """结构化日志记录器"""

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        log_dir: Optional[str] = None,
        log_file: Optional[str] = None,
        enable_console: bool = True,
        enable_json: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        初始化结构化日志记录器

        Args:
            name: 日志记录器名称
            level: 日志级别
            log_dir: 日志目录
            log_file: 日志文件名
            enable_console: 是否启用控制台输出
            enable_json: 是否启用 JSON 格式
            max_bytes: 单个日志文件最大大小
            backup_count: 备份文件数量
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers.clear()

        # 创建日志目录
        if log_dir:
            self.log_dir = Path(log_dir)
            self.log_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.log_dir = Path("logs")
            self.log_dir.mkdir(parents=True, exist_ok=True)

        # 日志文件
        if log_file is None:
            log_file = f"{name}.log"

        self.log_file = self.log_dir / log_file

        # 控制台处理器
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)

            if sys.stdout.isatty():
                console_formatter = ColorFormatter()
            else:
                console_formatter = logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
                )

            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        # 文件处理器（JSON 格式）
        if enable_json:
            file_handler = RotatingFileHandler(
                filename=str(self.log_file),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_formatter = JSONFormatter()
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

        # 上下文存储
        self._context: Dict[str, Any] = {}
        self._context_lock = threading.Lock()

    def add_context(self, **kwargs) -> None:
        """
        添加日志上下文

        Args:
            **kwargs: 上下文字段
        """
        with self._context_lock:
            self._context.update(kwargs)

    def clear_context(self) -> None:
        """清除日志上下文"""
        with self._context_lock:
            self._context.clear()

    def get_context(self) -> Dict[str, Any]:
        """
        获取当前上下文

        Returns:
            上下文字典
        """
        with self._context_lock:
            return self._context.copy()

    @contextmanager
    def context(self, **kwargs):
        """
        上下文管理器

        Args:
            **kwargs: 临时上下文字段

        使用:
            with logger.context(user_id="123", request_id="456"):
                logger.info("处理请求")
        """
        old_context = self.get_context()
        self.add_context(**kwargs)
        try:
            yield
        finally:
            self._context = old_context

    def _log_with_context(
        self,
        level: int,
        msg: str,
        *args,
        **kwargs
    ) -> None:
        """
        带上下文的日志记录

        Args:
            level: 日志级别
            msg: 消息
            *args: 格式化参数
            **kwargs: 额外字段
        """
        # 添加上下文到自定义字段（避免与 LogRecord 保留字段冲突）
        extra = kwargs.pop('extra', {})

        # 只添加非保留字段
        reserved_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
            'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
            'relativeCreated', 'thread', 'threadName', 'processName',
            'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info'
        }

        for key, value in self._context.items():
            if key not in reserved_fields:
                extra[key] = value

        # 添加自定义字段
        if extra:
            kwargs['extra'] = extra

        self.logger.log(level, msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs) -> None:
        """记录 DEBUG 级别日志"""
        self._log_with_context(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        """记录 INFO 级别日志"""
        self._log_with_context(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """记录 WARNING 级别日志"""
        self._log_with_context(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """记录 ERROR 级别日志"""
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        """记录 CRITICAL 级别日志"""
        self._log_with_context(logging.CRITICAL, msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        """记录异常日志"""
        kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)

    def set_level(self, level: int) -> None:
        """
        设置日志级别

        Args:
            level: 日志级别
        """
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)


# ============================================================================
# 日志装饰器
# ============================================================================

def log_execution(
    logger: Optional[StructuredLogger] = None,
    level: int = logging.INFO,
    include_args: bool = False,
    include_result: bool = False
):
    """
    日志装饰器 - 记录函数执行

    Args:
        logger: 日志记录器
        level: 日志级别
        include_args: 是否包含参数
        include_result: 是否包含返回值

    使用:
        @log_execution(include_args=True)
        def my_function(x, y):
            return x + y
    """
    if logger is None:
        logger = default_logger

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"

            log_data = {
                "event": "function_call",
                "function": func_name
            }

            if include_args:
                log_data["function_args"] = str(args)
                log_data["function_kwargs"] = str(kwargs)

            logger._log_with_context(level, f"调用函数: {func_name}", extra=log_data)

            try:
                result = func(*args, **kwargs)

                if include_result:
                    log_data["result"] = str(result)
                    logger._log_with_context(
                        level,
                        f"函数完成: {func_name}",
                        extra=log_data
                    )

                return result

            except Exception as e:
                log_data["error"] = str(e)
                logger._log_with_context(
                    logging.ERROR,
                    f"函数异常: {func_name}",
                    extra=log_data
                )
                raise

        return wrapper
    return decorator


def log_async_execution(
    logger: Optional[StructuredLogger] = None,
    level: int = logging.INFO,
    include_args: bool = False
):
    """
    异步函数日志装饰器

    Args:
        logger: 日志记录器
        level: 日志级别
        include_args: 是否包含参数
    """
    if logger is None:
        logger = default_logger

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"

            log_data = {
                "event": "async_function_call",
                "function": func_name
            }

            if include_args:
                log_data["function_args"] = str(args)
                log_data["function_kwargs"] = str(kwargs)

            logger._log_with_context(level, f"调用异步函数: {func_name}", extra=log_data)

            try:
                result = await func(*args, **kwargs)
                logger._log_with_context(
                    level,
                    f"异步函数完成: {func_name}",
                    extra=log_data
                )
                return result

            except Exception as e:
                log_data["error"] = str(e)
                logger._log_with_context(
                    logging.ERROR,
                    f"异步函数异常: {func_name}",
                    extra=log_data
                )
                raise

        return wrapper
    return decorator


# ============================================================================
# 日志管理器
# ============================================================================

class LogManager:
    """日志管理器"""

    def __init__(self):
        """初始化日志管理器"""
        self._loggers: Dict[str, StructuredLogger] = {}
        self._lock = threading.Lock()

    def get_logger(
        self,
        name: str,
        log_dir: Optional[str] = None,
        log_file: Optional[str] = None,
        **kwargs
    ) -> StructuredLogger:
        """
        获取或创建日志记录器

        Args:
            name: 日志记录器名称
            log_dir: 日志目录
            log_file: 日志文件
            **kwargs: 其他参数

        Returns:
            日志记录器
        """
        with self._lock:
            if name not in self._loggers:
                self._loggers[name] = StructuredLogger(
                    name=name,
                    log_dir=log_dir,
                    log_file=log_file,
                    **kwargs
                )
            return self._loggers[name]

    def remove_logger(self, name: str) -> None:
        """
        移除日志记录器

        Args:
            name: 日志记录器名称
        """
        with self._lock:
            if name in self._loggers:
                del self._loggers[name]

    def get_all_loggers(self) -> Dict[str, StructuredLogger]:
        """
        获取所有日志记录器

        Returns:
            日志记录器字典
        """
        with self._lock:
            return self._loggers.copy()

    def set_global_level(self, level: int) -> None:
        """
        设置全局日志级别

        Args:
            level: 日志级别
        """
        with self._lock:
            for logger in self._loggers.values():
                logger.set_level(level)


# ============================================================================
# 默认实例
# ============================================================================

# 日志管理器
log_manager = LogManager()

# 默认日志记录器
default_logger = log_manager.get_logger(
    "xhs-ai-operator",
    log_dir="logs",
    level=logging.INFO
)


# ============================================================================
# 便捷函数
# ============================================================================

def get_logger(
    name: str,
    log_dir: Optional[str] = None,
    log_file: Optional[str] = None,
    **kwargs
) -> StructuredLogger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称
        log_dir: 日志目录
        log_file: 日志文件
        **kwargs: 其他参数

    Returns:
        日志记录器
    """
    return log_manager.get_logger(name, log_dir, log_file, **kwargs)


def setup_logging(
    level: int = logging.INFO,
    log_dir: str = "logs",
    log_file: str = "app.log"
) -> StructuredLogger:
    """
    设置日志系统

    Args:
        level: 日志级别
        log_dir: 日志目录
        log_file: 日志文件

    Returns:
        默认日志记录器
    """
    global default_logger

    default_logger = log_manager.get_logger(
        "xhs-ai-operator",
        log_dir=log_dir,
        log_file=log_file,
        level=level
    )

    return default_logger


# 导出
__all__ = [
    'LogLevel',
    'JSONFormatter',
    'ColorFormatter',
    'StructuredLogger',
    'LogManager',
    'log_execution',
    'log_async_execution',
    'log_manager',
    'default_logger',
    'get_logger',
    'setup_logging'
]
