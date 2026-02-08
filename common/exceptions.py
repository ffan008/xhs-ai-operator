"""
自定义异常类层次结构

定义系统中所有异常类型，提供细粒度的异常处理和友好的错误消息。
"""

from typing import Optional, Dict, Any
from datetime import datetime


# ============================================================================
# 基础异常类
# ============================================================================

class BaseError(Exception):
    """
    所有自定义异常的基类

    提供统一的异常接口，包括错误码、用户友好消息和详细上下文。
    """

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化异常

        Args:
            message: 技术错误消息（内部使用）
            error_code: 错误码，用于错误分类
            user_message: 用户友好的错误消息
            details: 额外的错误详情
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.user_message = user_message or self._default_user_message()
        self.details = details or {}
        self.timestamp = datetime.now()

    def _default_user_message(self) -> str:
        """生成默认的用户友好消息"""
        return "操作失败，请稍后重试"

    def to_dict(self) -> Dict[str, Any]:
        """将异常转换为字典格式"""
        return {
            "error_code": self.error_code,
            "message": self.user_message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


# ============================================================================
# 验证相关异常
# ============================================================================

class ValidationError(BaseError):
    """输入验证失败"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        user_message: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        if value is not None:
            details['invalid_value'] = str(value)[:100]  # 限制长度

        # 如果没有提供自定义用户消息，使用默认的
        final_user_message = user_message or (f"输入参数验证失败: {field}" if field else "输入参数验证失败")

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            user_message=final_user_message,
            details=details
        )


class CronExpressionError(ValidationError):
    """Cron 表达式验证失败"""

    def __init__(self, message: str, expression: str):
        super().__init__(
            message=message,
            field="cron_expression",
            value=expression,
            user_message=f"Cron 表达式无效: {expression}"
        )


class ParameterError(ValidationError):
    """参数验证失败"""

    def __init__(self, message: str, parameter: str, value: Optional[Any] = None):
        super().__init__(
            message=message,
            field=parameter,
            value=value,
            user_message=f"参数 '{parameter}' 无效"
        )


# ============================================================================
# 配置相关异常
# ============================================================================

class ConfigurationError(BaseError):
    """配置错误"""

    def __init__(self, message: str, config_key: Optional[str] = None, user_message: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if config_key:
            details['config_key'] = config_key

        # 如果没有提供自定义用户消息，使用默认的
        final_user_message = user_message or (f"配置错误: {config_key}" if config_key else "配置错误")

        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            user_message=final_user_message,
            details=details
        )


class APIKeyError(ConfigurationError):
    """API 密钥错误"""

    def __init__(self, service: str, key_name: Optional[str] = None):
        super().__init__(
            message=f"API key not found for service: {service}",
            config_key=key_name or f"{service.lower()}_api_key",
            user_message=f"缺少 {service} 的 API 密钥配置"
        )


class ConfigFileError(ConfigurationError):
    """配置文件错误"""

    def __init__(self, message: str, file_path: str):
        super().__init__(
            message=message,
            config_key=file_path,
            user_message=f"配置文件错误: {file_path}"
        )
        self.details['file_path'] = file_path


# ============================================================================
# API 相关异常
# ============================================================================

class APIError(BaseError):
    """API 调用失败"""

    def __init__(
        self,
        message: str,
        service: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        user_message: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        details['service'] = service
        if status_code:
            details['status_code'] = status_code
        if response_body:
            # 限制响应体长度，避免日志过长
            details['response_body'] = response_body[:500]

        # 如果没有提供自定义用户消息，使用默认的
        final_user_message = user_message or f"调用 {service} API 失败"

        super().__init__(
            message=message,
            error_code="API_ERROR",
            user_message=final_user_message,
            details=details
        )


class APIConnectionError(APIError):
    """API 连接失败"""

    def __init__(self, service: str, reason: str = "连接超时"):
        super().__init__(
            message=f"Failed to connect to {service}: {reason}",
            service=service,
            user_message=f"无法连接到 {service}，请检查网络连接"
        )


class APIAuthenticationError(APIError):
    """API 认证失败"""

    def __init__(self, service: str):
        super().__init__(
            message=f"Authentication failed for {service}",
            service=service,
            status_code=401,
            user_message=f"{service} API 认证失败，请检查 API 密钥"
        )


class APIRateLimitError(APIError):
    """API 速率限制"""

    def __init__(
        self,
        service: str,
        retry_after: Optional[int] = None,
        limit: Optional[int] = None
    ):
        details = {}
        if retry_after:
            details['retry_after'] = retry_after
        if limit:
            details['rate_limit'] = limit

        super().__init__(
            message=f"Rate limit exceeded for {service}",
            service=service,
            status_code=429,
            user_message=f"{service} API 请求过于频繁，请稍后重试",
            details=details
        )


class APITimeoutError(APIError):
    """API 超时"""

    def __init__(self, service: str, timeout: float):
        super().__init__(
            message=f"Request to {service} timed out after {timeout}s",
            service=service,
            user_message=f"{service} API 请求超时，请稍后重试"
        )
        self.details['timeout'] = timeout


# ============================================================================
# 文件操作相关异常
# ============================================================================

class FileError(BaseError):
    """文件操作错误"""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        user_message: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if file_path:
            details['file_path'] = file_path
        if operation:
            details['operation'] = operation

        # 如果没有提供自定义用户消息，使用默认的
        final_user_message = user_message or f"文件操作失败: {operation or '未知操作'}"

        super().__init__(
            message=message,
            error_code="FILE_ERROR",
            user_message=final_user_message,
            details=details
        )


class FileNotFoundError(FileError):
    """文件未找到"""

    def __init__(self, file_path: str):
        super().__init__(
            message=f"File not found: {file_path}",
            file_path=file_path,
            operation="read",
            user_message=f"文件不存在: {file_path}"
        )


class FilePermissionError(FileError):
    """文件权限错误"""

    def __init__(self, file_path: str, operation: str = "access"):
        super().__init__(
            message=f"Permission denied: {file_path}",
            file_path=file_path,
            operation=operation,
            user_message=f"没有权限访问文件: {file_path}"
        )


class FileSecurityError(FileError):
    """文件安全错误（路径遍历等）"""

    def __init__(self, message: str, file_path: str):
        super().__init__(
            message=message,
            file_path=file_path,
            operation="validate",
            user_message=f"文件路径不安全: {file_path}"
        )


# ============================================================================
# 数据库相关异常
# ============================================================================

class DatabaseError(BaseError):
    """数据库错误"""

    def __init__(
        self,
        message: str,
        table: Optional[str] = None,
        operation: Optional[str] = None
    ):
        details = {}
        if table:
            details['table'] = table
        if operation:
            details['operation'] = operation

        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            user_message="数据库操作失败",
            details=details
        )


class DatabaseConnectionError(DatabaseError):
    """数据库连接失败"""

    def __init__(self, message: str = "Failed to connect to database"):
        super().__init__(
            message=message,
            user_message="无法连接到数据库，请检查数据库配置"
        )


class DatabaseQueryError(DatabaseError):
    """数据库查询错误"""

    def __init__(self, message: str, query: Optional[str] = None):
        details = {}
        if query:
            # 限制查询长度，避免日志过长
            details['query'] = query[:200]

        super().__init__(
            message=message,
            operation="query",
            user_message="数据库查询失败",
            details=details
        )


# ============================================================================
# 业务逻辑相关异常
# ============================================================================

class BusinessError(BaseError):
    """业务逻辑错误"""

    def __init__(self, message: str, user_message: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})

        super().__init__(
            message=message,
            error_code="BUSINESS_ERROR",
            user_message=user_message or "操作失败",
            details=details
        )


class WorkflowError(BusinessError):
    """工作流错误"""

    def __init__(self, message: str, workflow: Optional[str] = None):
        details = {}
        if workflow:
            details['workflow'] = workflow

        super().__init__(
            message=message,
            user_message=f"工作流执行失败: {workflow}" if workflow else "工作流执行失败",
            details=details
        )


class PublishError(BusinessError):
    """发布失败"""

    def __init__(self, message: str, platform: str = "小红书"):
        super().__init__(
            message=message,
            user_message=f"发布到 {platform} 失败: {message}"
        )


class ContentGenerationError(BusinessError):
    """内容生成失败"""

    def __init__(self, message: str, content_type: str = "内容"):
        super().__init__(
            message=message,
            user_message=f"{content_type}生成失败，请稍后重试"
        )


class SchedulerError(BusinessError):
    """调度器错误"""

    def __init__(self, message: str, job_id: Optional[str] = None):
        details = {}
        if job_id:
            details['job_id'] = job_id

        super().__init__(
            message=message,
            user_message="定时任务操作失败",
            details=details
        )


# ============================================================================
# 安全相关异常
# ============================================================================

class SecurityError(BaseError):
    """安全相关错误"""

    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="SECURITY_ERROR",
            user_message=user_message or "安全检查失败"
        )


class AuthenticationError(SecurityError):
    """认证失败"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            user_message="认证失败，请检查凭据"
        )


class AuthorizationError(SecurityError):
    """授权失败"""

    def __init__(self, resource: str, action: str):
        super().__init__(
            message=f"Authorization denied: {action} on {resource}",
            user_message=f"没有权限执行操作: {action}"
        )
        self.details['resource'] = resource
        self.details['action'] = action


class InputSanitizationError(SecurityError):
    """输入清理失败"""

    def __init__(self, message: str, input_type: str = "unknown"):
        super().__init__(
            message=message,
            user_message=f"输入包含不安全内容: {input_type}"
        )
        self.details['input_type'] = input_type


# ============================================================================
# 便捷函数
# ============================================================================

def handle_exception(
    exc: Exception,
    context: Optional[Dict[str, Any]] = None,
    logger: Optional[Any] = None
) -> BaseError:
    """
    将任意异常转换为自定义异常

    Args:
        exc: 原始异常
        context: 额外的上下文信息
        logger: 日志记录器

    Returns:
        自定义异常实例
    """
    # 如果已经是自定义异常，直接返回
    if isinstance(exc, BaseError):
        return exc

    # 根据异常类型转换为对应的自定义异常
    exception_mapping = {
        ValueError: ValidationError,
        KeyError: ConfigurationError,
        ConnectionError: APIConnectionError,
        TimeoutError: APITimeoutError,
        PermissionError: FilePermissionError,
        FileNotFoundError: FileNotFoundError,
    }

    exc_type = type(exc)
    for base_type, custom_type in exception_mapping.items():
        if isinstance(exc, base_type):
            return custom_type(
                message=str(exc),
                details={"original_exception": exc_type.__name__, **(context or {})}
            )

    # 默认转换为 BaseError
    return BaseError(
        message=str(exc),
        error_code="UNKNOWN_ERROR",
        details={"original_exception": exc_type.__name__, **(context or {})}
    )


def format_error_response(error: BaseError, include_details: bool = False) -> Dict[str, Any]:
    """
    格式化错误响应

    Args:
        error: 异常实例
        include_details: 是否包含详细错误信息

    Returns:
        格式化的错误响应字典
    """
    response = {
        "error_code": error.error_code,
        "message": error.user_message,
        "timestamp": error.timestamp.isoformat()
    }

    if include_details:
        response["details"] = error.details

    return response
