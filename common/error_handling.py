"""
错误处理工具

提供重试机制、错误信息脱敏、错误日志记录等功能。
"""

import time
import functools
import logging
import traceback
from typing import Callable, Type, Tuple, Optional, Any, Dict, List, TypeVar
from datetime import datetime
from .exceptions import BaseError, APIError, APITimeoutError, APIConnectionError


# ============================================================================
# 类型变量
# ============================================================================

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


# ============================================================================
# 重试机制
# ============================================================================

class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on: Tuple[Type[Exception], ...] = (Exception,),
        retry_on_error_codes: Optional[List[str]] = None
    ):
        """
        初始化重试配置

        Args:
            max_attempts: 最大尝试次数（包括第一次）
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            exponential_base: 指数退避的基数
            jitter: 是否添加随机抖动
            retry_on: 需要重试的异常类型
            retry_on_error_codes: 需要重试的错误码列表
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on = retry_on
        self.retry_on_error_codes = retry_on_error_codes or []


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: Optional[Tuple[Type[Exception], ...]] = None,
    retry_on_error_codes: Optional[List[str]] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[F], F]:
    """
    重试装饰器

    使用指数退避算法进行重试，适用于可能暂时失败的操作（如 API 调用）。

    Args:
        max_attempts: 最大尝试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exponential_base: 指数退避基数
        jitter: 是否添加随机抖动（避免惊群效应）
        retry_on: 需要重试的异常类型
        retry_on_error_codes: 需要重试的错误码列表
        logger: 日志记录器

    Returns:
        装饰器函数

    Example:
        @retry(max_attempts=3, base_delay=1.0)
        def call_api():
            # 可能失败的 API 调用
            pass
    """
    if retry_on is None:
        retry_on = (APIConnectionError, APITimeoutError, ConnectionError, TimeoutError)

    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retry_on=retry_on,
        retry_on_error_codes=retry_on_error_codes
    )

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    # 检查是否是 BaseError 且错误码在重试列表中
                    should_retry = True
                    if isinstance(e, BaseError):
                        if config.retry_on_error_codes:
                            should_retry = e.error_code in config.retry_on_error_codes

                    # 最后一次尝试不再重试
                    if attempt == config.max_attempts:
                        break

                    if not should_retry:
                        # 不应该重试的异常，直接抛出
                        raise

                    # 计算延迟时间
                    delay = min(
                        config.base_delay * (config.exponential_base ** (attempt - 1)),
                        config.max_delay
                    )

                    # 添加抖动
                    if config.jitter:
                        import random
                        delay = delay * (0.5 + random.random())

                    # 记录日志
                    if logger:
                        logger.warning(
                            f"Attempt {attempt}/{config.max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )

                    time.sleep(delay)

            # 所有尝试都失败了
            if logger:
                logger.error(
                    f"All {config.max_attempts} attempts failed for {func.__name__}"
                )

            raise last_exception

        return wrapper  # type: ignore

    return decorator


# ============================================================================
# 错误信息脱敏
# ============================================================================

class ErrorSanitizer:
    """
    错误信息脱敏器

    清理错误消息中的敏感信息（如 API 密钥、密码等）。
    """

    # 敏感信息模式
    SENSITIVE_PATTERNS = [
        # API 密钥
        (r'sk-[a-zA-Z0-9]{20,}', '[API_KEY_REDACTED]'),
        (r'r8_[a-zA-Z0-9]{20,}', '[API_TOKEN_REDACTED]'),
        (r'hf_[a-zA-Z0-9]{20,}', '[API_KEY_REDACTED]'),
        (r'Bearer\s+[a-zA-Z0-9+/=_]{20,}', '[BEARER_TOKEN_REDACTED]'),

        # 密码
        (r'password[\'":\s]*=\s*[\'"]?[^\'"\s]{8,}', 'password=[REDACTED]'),
        (r'passwd[\'":\s]*=\s*[\'"]?[^\'"\s]{8,}', 'passwd=[REDACTED]'),

        # URL 中的密钥
        (r'(https?://[^\s]*?)key=[a-zA-Z0-9+/]{20,}', r'\1key=[REDACTED]'),
        (r'(https?://[^\s]*?)token=[a-zA-Z0-9+/]{20,}', r'\1token=[REDACTED]'),

        # IP 地址
        (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP_ADDRESS_REDACTED]'),

        # 邮箱
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),
    ]

    @staticmethod
    def sanitize_error_message(message: str) -> str:
        """
        清理错误消息中的敏感信息

        Args:
            message: 原始错误消息

        Returns:
            清理后的错误消息
        """
        import re

        sanitized = message
        for pattern, replacement in ErrorSanitizer.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    @staticmethod
    def sanitize_exception(exc: Exception) -> Dict[str, Any]:
        """
        清理异常信息中的敏感数据

        Args:
            exc: 异常实例

        Returns:
            清理后的异常信息字典
        """
        import traceback

        # 清理异常消息
        message = ErrorSanitizer.sanitize_error_message(str(exc))

        # 清理堆栈跟踪中的敏感信息
        stack_trace = traceback.format_exc()
        sanitized_stack = ErrorSanitizer.sanitize_error_message(stack_trace)

        return {
            "type": type(exc).__name__,
            "message": message,
            "sanitized_stack_trace": sanitized_stack,
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# 错误日志记录
# ============================================================================

class ErrorLogger:
    """
    增强的错误日志记录器

    提供结构化的错误日志记录，包含上下文信息。
    """

    def __init__(self, logger: logging.Logger, include_stack: bool = True):
        """
        初始化错误日志记录器

        Args:
            logger: 日志记录器
            include_stack: 是否包含堆栈跟踪
        """
        self.logger = logger
        self.include_stack = include_stack

    def log_exception(
        self,
        exc: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: int = logging.ERROR
    ):
        """
        记录异常

        Args:
            exc: 异常实例
            context: 额外的上下文信息
            level: 日志级别
        """
        # 清理敏感信息
        if isinstance(exc, BaseError):
            # 自定义异常
            error_info = {
                "error_code": exc.error_code,
                "message": ErrorSanitizer.sanitize_error_message(exc.message),
                "user_message": exc.user_message,
                "timestamp": exc.timestamp.isoformat()
            }
            if exc.details:
                error_info["details"] = exc.details
        else:
            # 标准异常
            error_info = ErrorSanitizer.sanitize_exception(exc)

        # 添加上下文
        if context:
            error_info["context"] = context

        # 记录日志
        self.logger.log(
            level,
            f"Exception occurred: {error_info.get('error_code', type(exc).__name__)}",
            extra={"error_info": error_info}
        )

        # 记录堆栈跟踪
        if self.include_stack:
            self.logger.log(
                level,
                f"Stack trace:\n{ErrorSanitizer.sanitize_error_message(traceback.format_exc())}"
            )

    def log_api_error(
        self,
        service: str,
        exc: Exception,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        """
        记录 API 错误

        Args:
            service: API 服务名称
            exc: 异常实例
            request_data: 请求数据（会清理敏感信息）
            response_data: 响应数据
        """
        context = {
            "service": service,
            "error_type": type(exc).__name__
        }

        # 清理请求数据中的敏感信息
        if request_data:
            sanitized_request = {}
            for key, value in request_data.items():
                if key.lower() in ['api_key', 'token', 'password', 'secret']:
                    sanitized_request[key] = '[REDACTED]'
                elif isinstance(value, str):
                    sanitized_request[key] = ErrorSanitizer.sanitize_error_message(value)
                else:
                    sanitized_request[key] = value
            context["request"] = sanitized_request

        # 添加响应数据（不包含敏感信息）
        if response_data:
            context["response"] = response_data

        self.log_exception(exc, context=context)


# ============================================================================
# 错误处理装饰器
# ============================================================================

def handle_errors(
    logger: Optional[logging.Logger] = None,
    raise_on_error: bool = True,
    error_handler: Optional[Callable[[Exception], Any]] = None,
    default_return: Any = None
) -> Callable[[F], F]:
    """
    错误处理装饰器

    统一处理函数中的异常，提供日志记录和可选的错误恢复。

    Args:
        logger: 日志记录器
        raise_on_error: 是否在错误时重新抛出异常
        error_handler: 自定义错误处理函数
        default_return: 发生错误时的默认返回值（当 raise_on_error=False 时）

    Returns:
        装饰器函数

    Example:
        @handle_errors(logger=logger, raise_on_error=False, default_return=None)
        def risky_operation():
            # 可能失败的操作
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录日志
                if logger:
                    error_logger = ErrorLogger(logger)
                    error_logger.log_exception(e, context={"function": func.__name__})

                # 自定义错误处理
                if error_handler:
                    return error_handler(e)

                # 重新抛出异常
                if raise_on_error:
                    raise

                # 返回默认值
                return default_return

        return wrapper  # type: ignore

    return decorator


# ============================================================================
# 上下文管理器
# ============================================================================

class ErrorContext:
    """
    错误上下文管理器

    提供上下文相关的错误处理和日志记录。
    """

    def __init__(
        self,
        operation_name: str,
        logger: Optional[logging.Logger] = None,
        raise_on_error: bool = True
    ):
        """
        初始化错误上下文

        Args:
            operation_name: 操作名称
            logger: 日志记录器
            raise_on_error: 是否在错误时重新抛出异常
        """
        self.operation_name = operation_name
        self.logger = logger
        self.raise_on_error = raise_on_error
        self.error_logger = ErrorLogger(logger) if logger else None
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        if self.logger:
            self.logger.info(f"Starting operation: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # 没有异常
            duration = time.time() - self.start_time
            if self.logger:
                self.logger.info(
                    f"Operation '{self.operation_name}' completed successfully in {duration:.2f}s"
                )
            return False

        # 有异常
        duration = time.time() - self.start_time
        if self.error_logger:
            self.error_logger.log_exception(
                exc_val,
                context={
                    "operation": self.operation_name,
                    "duration": f"{duration:.2f}s"
                }
            )

        return not self.raise_on_error


# ============================================================================
# 便捷函数
# ============================================================================

def safe_execute(
    func: Callable[..., T],
    *args,
    default_value: T = None,
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> T:
    """
    安全执行函数，捕获并记录异常

    Args:
        func: 要执行的函数
        *args: 位置参数
        default_value: 发生异常时的默认返回值
        logger: 日志记录器
        **kwargs: 关键字参数

    Returns:
        函数返回值或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if logger:
            error_logger = ErrorLogger(logger)
            error_logger.log_exception(e, context={"function": func.__name__})
        return default_value


def format_exception_for_user(exc: Exception) -> str:
    """
    格式化异常为用户友好的消息

    Args:
        exc: 异常实例

    Returns:
        用户友好的错误消息
    """
    if isinstance(exc, BaseError):
        return exc.user_message
    else:
        # 对标准异常也提供友好的消息
        exception_messages = {
            ConnectionError: "网络连接失败，请检查网络设置",
            TimeoutError: "操作超时，请稍后重试",
            PermissionError: "权限不足，请检查文件权限",
            FileNotFoundError: "文件不存在",
            ValueError: "输入参数无效",
            KeyError: "缺少必需的配置项",
        }

        for exc_type, message in exception_messages.items():
            if isinstance(exc, exc_type):
                return message

        return "操作失败，请稍后重试"
