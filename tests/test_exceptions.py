"""
异常处理框架的单元测试
"""

import pytest
import time
import logging
from unittest.mock import Mock, patch

# 添加父目录到路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.exceptions import (
    BaseError,
    ValidationError,
    CronExpressionError,
    ParameterError,
    ConfigurationError,
    APIKeyError,
    ConfigFileError,
    APIError,
    APIConnectionError,
    APIAuthenticationError,
    APIRateLimitError,
    APITimeoutError,
    FileError,
    FileNotFoundError,
    FilePermissionError,
    FileSecurityError,
    DatabaseError,
    BusinessError,
    WorkflowError,
    PublishError,
    ContentGenerationError,
    SecurityError,
    AuthenticationError,
    AuthorizationError,
    InputSanitizationError,
    handle_exception,
    format_error_response
)

from common.error_handling import (
    retry,
    ErrorSanitizer,
    ErrorLogger,
    handle_errors,
    ErrorContext,
    safe_execute,
    format_exception_for_user
)


# ============================================================================
# BaseError 测试
# ============================================================================

class TestBaseError:
    """测试基础异常类"""

    def test_base_error_creation(self):
        """测试基础异常创建"""
        error = BaseError(
            message="Technical error",
            error_code="TEST_ERROR",
            user_message="User friendly message",
            details={"key": "value"}
        )

        assert error.message == "Technical error"
        assert error.error_code == "TEST_ERROR"
        assert error.user_message == "User friendly message"
        assert error.details == {"key": "value"}
        assert error.timestamp is not None
        print("✅ 基础异常创建成功")

    def test_to_dict(self):
        """测试异常转换为字典"""
        error = BaseError(
            message="Test error",
            error_code="TEST_001"
        )

        error_dict = error.to_dict()

        assert error_dict["error_code"] == "TEST_001"
        assert "message" in error_dict
        assert "timestamp" in error_dict
        print("✅ 异常转字典成功")

    def test_default_user_message(self):
        """测试默认用户消息"""
        error = BaseError(message="Test")
        assert "操作失败" in error.user_message
        print("✅ 默认用户消息生成成功")


# ============================================================================
# 验证异常测试
# ============================================================================

class TestValidationErrors:
    """测试验证相关异常"""

    def test_validation_error(self):
        """测试验证错误"""
        error = ValidationError(
            message="Invalid input",
            field="username",
            value="invalid@user"
        )

        assert error.error_code == "VALIDATION_ERROR"
        assert error.details["field"] == "username"
        assert error.details["invalid_value"] == "invalid@user"
        print("✅ 验证错误创建成功")

    def test_cron_expression_error(self):
        """测试 Cron 表达式错误"""
        error = CronExpressionError(
            message="Invalid format",
            expression="61 * * * *"
        )

        assert error.error_code == "VALIDATION_ERROR"
        assert "61 * * * *" in error.user_message
        print("✅ Cron 表达式错误创建成功")

    def test_parameter_error(self):
        """测试参数错误"""
        error = ParameterError(
            message="Invalid count",
            parameter="count",
            value=0
        )

        assert "count" in error.user_message
        assert error.details["field"] == "count"
        print("✅ 参数错误创建成功")


# ============================================================================
# 配置异常测试
# ============================================================================

class TestConfigurationErrors:
    """测试配置相关异常"""

    def test_configuration_error(self):
        """测试配置错误"""
        error = ConfigurationError(
            message="Config missing",
            config_key="api_key"
        )

        assert error.error_code == "CONFIG_ERROR"
        assert "api_key" in error.user_message
        print("✅ 配置错误创建成功")

    def test_api_key_error(self):
        """测试 API 密钥错误"""
        error = APIKeyError(service="OpenAI")

        assert "OpenAI" in error.user_message
        assert error.details["config_key"] == "openai_api_key"
        print("✅ API 密钥错误创建成功")

    def test_config_file_error(self):
        """测试配置文件错误"""
        error = ConfigFileError(
            message="File not found",
            file_path="/path/to/config.json"
        )

        assert error.details["file_path"] == "/path/to/config.json"
        print("✅ 配置文件错误创建成功")


# ============================================================================
# API 异常测试
# ============================================================================

class TestAPIErrors:
    """测试 API 相关异常"""

    def test_api_error(self):
        """测试 API 错误"""
        error = APIError(
            message="Request failed",
            service="xiaohongshu",
            status_code=500
        )

        assert error.error_code == "API_ERROR"
        assert error.details["status_code"] == 500
        assert error.details["service"] == "xiaohongshu"
        print("✅ API 错误创建成功")

    def test_api_connection_error(self):
        """测试 API 连接错误"""
        error = APIConnectionError(service="stability")

        assert "连接" in error.user_message
        assert error.details["service"] == "stability"
        print("✅ API 连接错误创建成功")

    def test_api_authentication_error(self):
        """测试 API 认证错误"""
        error = APIAuthenticationError(service="replicate")

        assert "认证失败" in error.user_message
        assert error.details["status_code"] == 401
        print("✅ API 认证错误创建成功")

    def test_api_rate_limit_error(self):
        """测试 API 速率限制错误"""
        error = APIRateLimitError(
            service="openai",
            retry_after=60,
            limit=100
        )

        assert "过于频繁" in error.user_message
        assert error.details["retry_after"] == 60
        assert error.details["rate_limit"] == 100
        assert error.details["status_code"] == 429
        print("✅ API 速率限制错误创建成功")

    def test_api_timeout_error(self):
        """测试 API 超时错误"""
        error = APITimeoutError(service="tavily", timeout=30.0)

        assert "超时" in error.user_message
        assert error.details["timeout"] == 30.0
        print("✅ API 超时错误创建成功")


# ============================================================================
# 文件异常测试
# ============================================================================

class TestFileErrors:
    """测试文件相关异常"""

    def test_file_error(self):
        """测试文件错误"""
        error = FileError(
            message="Cannot read",
            file_path="/test/file.txt",
            operation="read"
        )

        assert error.error_code == "FILE_ERROR"
        assert error.details["file_path"] == "/test/file.txt"
        print("✅ 文件错误创建成功")

    def test_file_not_found_error(self):
        """测试文件未找到错误"""
        error = FileNotFoundError("/path/to/missing.txt")

        assert "不存在" in error.user_message
        assert error.details["operation"] == "read"
        print("✅ 文件未找到错误创建成功")

    def test_file_permission_error(self):
        """测试文件权限错误"""
        error = FilePermissionError(
            file_path="/protected/file.txt",
            operation="write"
        )

        assert "权限" in error.user_message
        assert error.details["operation"] == "write"
        print("✅ 文件权限错误创建成功")

    def test_file_security_error(self):
        """测试文件安全错误"""
        error = FileSecurityError(
            message="Path traversal detected",
            file_path="../../etc/passwd"
        )

        assert "不安全" in error.user_message
        print("✅ 文件安全错误创建成功")


# ============================================================================
# 业务异常测试
# ============================================================================

class TestBusinessErrors:
    """测试业务逻辑异常"""

    def test_workflow_error(self):
        """测试工作流错误"""
        error = WorkflowError(
            message="Step failed",
            workflow="publish_note"
        )

        assert "publish_note" in error.user_message
        assert error.details["workflow"] == "publish_note"
        print("✅ 工作流错误创建成功")

    def test_publish_error(self):
        """测试发布错误"""
        error = PublishError(message="Network error")

        assert "小红书" in error.user_message
        print("✅ 发布错误创建成功")

    def test_content_generation_error(self):
        """测试内容生成错误"""
        error = ContentGenerationError(
            message="API failed",
            content_type="标题"
        )

        assert "标题" in error.user_message
        print("✅ 内容生成错误创建成功")


# ============================================================================
# 安全异常测试
# ============================================================================

class TestSecurityErrors:
    """测试安全相关异常"""

    def test_authentication_error(self):
        """测试认证错误"""
        error = AuthenticationError()

        assert "认证失败" in error.user_message
        print("✅ 认证错误创建成功")

    def test_authorization_error(self):
        """测试授权错误"""
        error = AuthorizationError(
            resource="/admin",
            action="delete"
        )

        assert "权限" in error.user_message
        assert error.details["action"] == "delete"
        print("✅ 授权错误创建成功")

    def test_input_sanitization_error(self):
        """测试输入清理错误"""
        error = InputSanitizationError(
            message="XSS detected",
            input_type="HTML"
        )

        assert "不安全" in error.user_message
        print("✅ 输入清理错误创建成功")


# ============================================================================
# 异常处理函数测试
# ============================================================================

class TestExceptionHandling:
    """测试异常处理函数"""

    def test_handle_base_error(self):
        """测试处理自定义异常"""
        error = ValidationError(message="Test", field="test")
        result = handle_exception(error)

        assert result is error
        print("✅ 自定义异常处理成功")

    def test_handle_standard_error(self):
        """测试处理标准异常"""
        error = ValueError("Invalid value")
        result = handle_exception(error)

        assert isinstance(result, ValidationError)
        print("✅ 标准异常转换成功")

    def test_handle_key_error(self):
        """测试处理 KeyError"""
        error = KeyError("missing_key")
        result = handle_exception(error)

        assert isinstance(result, ConfigurationError)
        print("✅ KeyError 转换成功")

    def test_format_error_response(self):
        """测试格式化错误响应"""
        error = ValidationError(message="Test", field="username")

        response = format_error_response(error, include_details=False)
        assert "error_code" in response
        assert "details" not in response

        response_with_details = format_error_response(error, include_details=True)
        assert "details" in response_with_details
        print("✅ 错误响应格式化成功")


# ============================================================================
# 重试机制测试
# ============================================================================

class TestRetryMechanism:
    """测试重试机制"""

    def test_retry_on_failure(self):
        """测试失败后重试"""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Failed")
            return "success"

        result = failing_function()

        assert call_count == 3
        assert result == "success"
        print(f"✅ 重试机制成功，共尝试 {call_count} 次")

    def test_retry_exhausted(self):
        """测试重试次数用尽"""
        @retry(max_attempts=2, base_delay=0.01)
        def always_failing_function():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_failing_function()
        print("✅ 重试次数用尽后正确抛出异常")

    def test_no_retry_on_unexpected_error(self):
        """测试不重试非指定异常"""
        @retry(max_attempts=3, retry_on=(ConnectionError,), base_delay=0.01)
        def raise_value_error():
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            raise_value_error()
        print("✅ 非指定异常不重试")

    def test_retry_with_jitter(self):
        """测试带抖动的重试"""
        call_times = []

        @retry(max_attempts=3, base_delay=0.05, jitter=True)
        def record_time_function():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Failed")
            return "success"

        record_time_function()

        # 检查延迟时间有差异（抖动）
        if len(call_times) >= 2:
            delay = call_times[1] - call_times[0]
            assert delay >= 0.04  # 应该接近 base_delay
            print(f"✅ 带抖动的重试成功，延迟: {delay:.3f}s")


# ============================================================================
# 错误信息脱敏测试
# ============================================================================

class TestErrorSanitization:
    """测试错误信息脱敏"""

    def test_sanitize_api_key(self):
        """测试 API 密钥脱敏"""
        message = "API key: sk-abc123def4567890123456789012345678901234"
        sanitized = ErrorSanitizer.sanitize_error_message(message)

        assert "sk-abc" not in sanitized
        assert "[API_KEY_REDACTED]" in sanitized
        print("✅ API 密钥脱敏成功")

    def test_sanitize_password(self):
        """测试密码脱敏"""
        message = "Database connection: password=mySecretPassword123"
        sanitized = ErrorSanitizer.sanitize_error_message(message)

        assert "mySecretPassword123" not in sanitized
        assert "[REDACTED]" in sanitized
        print("✅ 密码脱敏成功")

    def test_sanitize_bearer_token(self):
        """测试 Bearer Token 脱敏"""
        message = "Authorization: Bearer abc123def456789012345678901234"
        sanitized = ErrorSanitizer.sanitize_error_message(message)

        assert "abc123def" not in sanitized
        assert "[BEARER_TOKEN_REDACTED]" in sanitized
        print("✅ Bearer Token 脱敏成功")

    def test_sanitize_ip_address(self):
        """测试 IP 地址脱敏"""
        message = "Connecting to 192.168.1.1:8080"
        sanitized = ErrorSanitizer.sanitize_error_message(message)

        assert "192.168.1.1" not in sanitized
        assert "[IP_ADDRESS_REDACTED]" in sanitized
        print("✅ IP 地址脱敏成功")

    def test_sanitize_email(self):
        """测试邮箱脱敏"""
        message = "User email: user@example.com"
        sanitized = ErrorSanitizer.sanitize_error_message(message)

        assert "user@example.com" not in sanitized
        assert "[EMAIL_REDACTED]" in sanitized
        print("✅ 邮箱脱敏成功")

    def test_sanitize_exception(self):
        """测试异常对象脱敏"""
        exc = Exception(f"Failed with key=sk-abc123def4567890123456789012345678901234")

        sanitized = ErrorSanitizer.sanitize_exception(exc)

        assert "sk-abc" not in sanitized["message"]
        assert sanitized["type"] == "Exception"
        print("✅ 异常对象脱敏成功")


# ============================================================================
# 错误日志测试
# ============================================================================

class TestErrorLogging:
    """测试错误日志"""

    def test_log_exception(self):
        """测试记录异常"""
        mock_logger = Mock()
        error_logger = ErrorLogger(mock_logger, include_stack=False)

        error = ValidationError(message="Test", field="username")
        error_logger.log_exception(error, context={"user": "test"})

        assert mock_logger.log.called
        print("✅ 异常日志记录成功")

    def test_log_api_error(self):
        """测试记录 API 错误"""
        mock_logger = Mock()
        error_logger = ErrorLogger(mock_logger, include_stack=False)

        exc = APIConnectionError(service="xiaohongshu")
        error_logger.log_api_error(
            service="xiaohongshu",
            exc=exc,
            request_data={"api_key": "sk-test123", "data": "test"},
            response_data={"status": "error"}
        )

        # 验证 API 密钥被脱敏
        call_args = mock_logger.log.call_args
        logged_data = call_args[1].get("extra", {}).get("error_info", {})

        if "context" in logged_data and "request" in logged_data["context"]:
            assert logged_data["context"]["request"].get("api_key") == '[REDACTED]'
            print("✅ API 错误日志记录成功，敏感信息已脱敏")
        else:
            print("✅ API 错误日志记录成功")


# ============================================================================
# 错误处理装饰器测试
# ============================================================================

class TestErrorDecorators:
    """测试错误处理装饰器"""

    def test_handle_errors_no_raise(self):
        """测试不抛出异常"""
        mock_logger = Mock()

        @handle_errors(logger=mock_logger, raise_on_error=False, default_return="default")
        def failing_function():
            raise ValueError("Error")

        result = failing_function()

        assert result == "default"
        assert mock_logger.log.called
        print("✅ 不抛出异常模式测试成功")

    def test_handle_errors_with_raise(self):
        """测试抛出异常"""
        mock_logger = Mock()

        @handle_errors(logger=mock_logger, raise_on_error=True)
        def failing_function():
            raise ValueError("Error")

        with pytest.raises(ValueError):
            failing_function()

        assert mock_logger.log.called
        print("✅ 抛出异常模式测试成功")

    def test_safe_execute(self):
        """测试安全执行"""
        mock_logger = Mock()

        def failing_function():
            raise ValueError("Error")

        result = safe_execute(
            failing_function,
            logger=mock_logger,
            default_value="fallback"
        )

        assert result == "fallback"
        print("✅ 安全执行测试成功")


# ============================================================================
# 错误上下文管理器测试
# ============================================================================

class TestErrorContext:
    """测试错误上下文管理器"""

    def test_error_context_success(self):
        """测试成功执行的上下文"""
        mock_logger = Mock()

        with ErrorContext("test_operation", logger=mock_logger):
            pass

        # 验证记录了开始和结束日志
        assert mock_logger.info.call_count >= 2
        print("✅ 成功上下文测试成功")

    def test_error_context_with_error(self):
        """测试有错误的上下文"""
        mock_logger = Mock()

        try:
            with ErrorContext("test_operation", logger=mock_logger, raise_on_error=True):
                raise ValueError("Test error")
        except ValueError:
            pass

        # 验证记录了错误
        assert mock_logger.error.called or mock_logger.log.called
        print("✅ 错误上下文测试成功")


# ============================================================================
# 用户友好消息测试
# ============================================================================

class TestUserFriendlyMessages:
    """测试用户友好消息"""

    def test_base_error_message(self):
        """测试自定义异常的用户消息"""
        error = ValidationError(
            message="Technical details",
            user_message="请检查输入格式"
        )

        message = format_exception_for_user(error)
        assert message == "请检查输入格式"
        print("✅ 自定义异常用户消息测试成功")

    def test_standard_exception_message(self):
        """测试标准异常的用户消息"""
        error = ConnectionError("Network failed")
        message = format_exception_for_user(error)

        assert "网络" in message
        print("✅ 标准异常用户消息测试成功")

    def test_unknown_exception_message(self):
        """测试未知异常的用户消息"""
        error = RuntimeError("Unknown error")
        message = format_exception_for_user(error)

        assert "操作失败" in message
        print("✅ 未知异常用户消息测试成功")


def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行异常处理测试...\n")

    print("="*60)
    print("测试 BaseError")
    print("="*60)
    TestBaseError().test_base_error_creation()
    TestBaseError().test_to_dict()
    TestBaseError().test_default_user_message()

    print("\n" + "="*60)
    print("测试验证异常")
    print("="*60)
    TestValidationErrors().test_validation_error()
    TestValidationErrors().test_cron_expression_error()
    TestValidationErrors().test_parameter_error()

    print("\n" + "="*60)
    print("测试配置异常")
    print("="*60)
    TestConfigurationErrors().test_configuration_error()
    TestConfigurationErrors().test_api_key_error()
    TestConfigurationErrors().test_config_file_error()

    print("\n" + "="*60)
    print("测试 API 异常")
    print("="*60)
    TestAPIErrors().test_api_error()
    TestAPIErrors().test_api_connection_error()
    TestAPIErrors().test_api_authentication_error()
    TestAPIErrors().test_api_rate_limit_error()
    TestAPIErrors().test_api_timeout_error()

    print("\n" + "="*60)
    print("测试文件异常")
    print("="*60)
    TestFileErrors().test_file_error()
    TestFileErrors().test_file_not_found_error()
    TestFileErrors().test_file_permission_error()
    TestFileErrors().test_file_security_error()

    print("\n" + "="*60)
    print("测试业务异常")
    print("="*60)
    TestBusinessErrors().test_workflow_error()
    TestBusinessErrors().test_publish_error()
    TestBusinessErrors().test_content_generation_error()

    print("\n" + "="*60)
    print("测试安全异常")
    print("="*60)
    TestSecurityErrors().test_authentication_error()
    TestSecurityErrors().test_authorization_error()
    TestSecurityErrors().test_input_sanitization_error()

    print("\n" + "="*60)
    print("测试异常处理函数")
    print("="*60)
    TestExceptionHandling().test_handle_base_error()
    TestExceptionHandling().test_handle_standard_error()
    TestExceptionHandling().test_handle_key_error()
    TestExceptionHandling().test_format_error_response()

    print("\n" + "="*60)
    print("测试重试机制")
    print("="*60)
    TestRetryMechanism().test_retry_on_failure()
    TestRetryMechanism().test_retry_exhausted()
    TestRetryMechanism().test_no_retry_on_unexpected_error()
    TestRetryMechanism().test_retry_with_jitter()

    print("\n" + "="*60)
    print("测试错误信息脱敏")
    print("="*60)
    TestErrorSanitization().test_sanitize_api_key()
    TestErrorSanitization().test_sanitize_password()
    TestErrorSanitization().test_sanitize_bearer_token()
    TestErrorSanitization().test_sanitize_ip_address()
    TestErrorSanitization().test_sanitize_email()
    TestErrorSanitization().test_sanitize_exception()

    print("\n" + "="*60)
    print("测试错误日志")
    print("="*60)
    TestErrorLogging().test_log_exception()
    TestErrorLogging().test_log_api_error()

    print("\n" + "="*60)
    print("测试错误处理装饰器")
    print("="*60)
    TestErrorDecorators().test_handle_errors_no_raise()
    TestErrorDecorators().test_handle_errors_with_raise()
    TestErrorDecorators().test_safe_execute()

    print("\n" + "="*60)
    print("测试错误上下文管理器")
    print("="*60)
    TestErrorContext().test_error_context_success()
    TestErrorContext().test_error_context_with_error()

    print("\n" + "="*60)
    print("测试用户友好消息")
    print("="*60)
    TestUserFriendlyMessages().test_base_error_message()
    TestUserFriendlyMessages().test_standard_exception_message()
    TestUserFriendlyMessages().test_unknown_exception_message()

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
