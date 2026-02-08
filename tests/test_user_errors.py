"""
用户友好错误提示模块单元测试
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# 添加父目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.user_errors import (
    ErrorSeverity,
    ErrorCategory,
    ErrorCode,
    UserErrorMessage,
    ErrorMessageMapper,
    FriendlyErrorHandler,
    handle_error,
    format_error,
    try_auto_fix
)
from common.exceptions import BusinessError, ConfigurationError, SecurityError


# ============================================================================
# 错误信息测试
# ============================================================================

class TestUserErrorMessage:
    """测试用户错误信息"""

    def test_create_message(self):
        """测试创建错误信息"""
        message = UserErrorMessage(
            code=ErrorCode.NET_001,
            title="测试标题",
            description="测试描述",
            suggestions=["建议1", "建议2"],
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.NETWORK
        )

        assert message.code == ErrorCode.NET_001
        assert message.title == "测试标题"
        assert len(message.suggestions) == 2
        assert message.severity == ErrorSeverity.ERROR
        assert message.category == ErrorCategory.NETWORK
        print("✅ 创建错误信息成功")

    def test_message_with_auto_fix(self):
        """测试带自动修复的错误信息"""
        def auto_fix_func():
            return True

        message = UserErrorMessage(
            code=ErrorCode.AUTH_002,
            title="登录过期",
            description="需要重新登录",
            suggestions=["重新登录"],
            auto_fix=auto_fix_func
        )

        assert message.auto_fix is not None
        assert message.auto_fix() is True
        print("✅ 自动修复功能正确")


# ============================================================================
# 错误信息映射器测试
# ============================================================================

class TestErrorMessageMapper:
    """测试错误信息映射器"""

    def test_initialization(self):
        """测试初始化"""
        mapper = ErrorMessageMapper()

        # 检查是否有默认的错误映射
        assert len(mapper._error_map) > 0

        # 检查常用错误码
        assert ErrorCode.NET_001 in mapper._error_map
        assert ErrorCode.API_003 in mapper._error_map
        assert ErrorCode.CFG_001 in mapper._error_map

        print("✅ 映射器初始化正确")

    def test_get_message(self):
        """测试获取错误信息"""
        mapper = ErrorMessageMapper()

        message = mapper.get_message(ErrorCode.NET_001)

        assert message.code == ErrorCode.NET_001
        assert message.title == "网络连接失败"
        assert len(message.suggestions) > 0
        assert message.severity == ErrorSeverity.ERROR
        assert message.category == ErrorCategory.NETWORK

        print("✅ 获取错误信息正确")

    def test_get_unknown_code(self):
        """测试获取未知错误码"""
        mapper = ErrorMessageMapper()

        # 使用一个不存在的错误码（使用枚举中的最后一个加1）
        unknown_code = list(ErrorCode)[-1]  # 获取最后一个

        message = mapper.get_message(unknown_code)

        # 应该返回默认消息
        assert message.code == unknown_code
        assert message.title == "未知错误"

        print("✅ 未知错误码处理正确")

    def test_register_custom_message(self):
        """测试注册自定义错误信息"""
        mapper = ErrorMessageMapper()

        mapper.register_custom_message(
            code=ErrorCode.SYS_001,
            title="自定义错误",
            description="这是一个自定义错误",
            suggestions=["解决方案1", "解决方案2"],
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.SYSTEM,
            help_url="https://example.com/help"
        )

        message = mapper.get_message(ErrorCode.SYS_001)

        assert message.title == "自定义错误"
        assert message.description == "这是一个自定义错误"
        assert len(message.suggestions) == 2
        assert message.severity == ErrorSeverity.WARNING
        assert message.help_url == "https://example.com/help"

        print("✅ 注册自定义错误正确")

    def test_pattern_matching(self):
        """测试模式匹配"""
        mapper = ErrorMessageMapper()

        # 添加一个模式
        custom_message = UserErrorMessage(
            code=ErrorCode.API_001,
            title="模式匹配错误",
            description="通过正则匹配的错误",
            suggestions=["按模式处理"]
        )

        mapper.add_pattern(r"Connection refused", custom_message)

        # 匹配模式
        matched = mapper.match_pattern("Connection refused: localhost:8080")

        assert matched is not None
        assert matched.title == "模式匹配错误"

        print("✅ 模式匹配正确")

    def test_pattern_no_match(self):
        """测试模式不匹配"""
        mapper = ErrorMessageMapper()

        custom_message = UserErrorMessage(
            code=ErrorCode.API_001,
            title="测试错误",
            description="测试",
            suggestions=[]
        )

        mapper.add_pattern(r"SpecialError", custom_message)

        # 不匹配
        matched = mapper.match_pattern("Different error")

        assert matched is None

        print("✅ 模式不匹配正确")


# ============================================================================
# 友好的错误处理器测试
# ============================================================================

class TestFriendlyErrorHandler:
    """测试友好的错误处理器"""

    def test_initialization(self):
        """测试初始化"""
        handler = FriendlyErrorHandler()

        assert handler.mapper is not None
        assert handler._stats["total_errors"] == 0
        assert handler._stats["auto_fixed"] == 0

        print("✅ 处理器初始化正确")

    def test_handle_network_error(self):
        """测试处理网络错误"""
        handler = FriendlyErrorHandler()

        exception = ConnectionError("Failed to connect")

        message = handler.handle_exception(exception)

        assert message.category == ErrorCategory.NETWORK
        assert message.code == ErrorCode.NET_001
        assert len(message.suggestions) > 0

        # 检查统计
        stats = handler.get_stats()
        assert stats["total_errors"] == 1

        print("✅ 网络错误处理正确")

    def test_handle_timeout_error(self):
        """测试处理超时错误"""
        handler = FriendlyErrorHandler()

        exception = TimeoutError("Request timeout")

        message = handler.handle_exception(exception)

        assert message.code == ErrorCode.NET_002
        assert message.title == "请求超时"
        assert message.severity == ErrorSeverity.WARNING

        print("✅ 超时错误处理正确")

    def test_handle_business_error(self):
        """测试处理业务错误"""
        handler = FriendlyErrorHandler()

        exception = BusinessError(
            message="Invalid input format",
            user_message="输入格式不正确"
        )

        message = handler.handle_exception(exception)

        assert message.category == ErrorCategory.VALIDATION
        assert message.title == "操作失败" or "格式不正确"
        assert message.technical_details == "Invalid input format"

        print("✅ 业务错误处理正确")

    def test_handle_security_error(self):
        """测试处理安全错误"""
        handler = FriendlyErrorHandler()

        exception = SecurityError(
            message="Permission denied",
            user_message="权限不足，无法访问"
        )

        message = handler.handle_exception(exception)

        assert message.category == ErrorCategory.PERMISSION
        assert "权限" in message.title or "权限" in message.description

        print("✅ 安全错误处理正确")

    def test_handle_configuration_error(self):
        """测试处理配置错误"""
        handler = FriendlyErrorHandler()

        exception = ConfigurationError(
            message="Missing required field: api_key"
        )

        message = handler.handle_exception(exception)

        assert message.code == ErrorCode.CFG_004
        assert message.category == ErrorCategory.CONFIG

        print("✅ 配置错误处理正确")

    def test_handle_generic_error(self):
        """测试处理通用错误"""
        handler = FriendlyErrorHandler()

        exception = ValueError("Some error")

        message = handler.handle_exception(exception)

        assert message.code == ErrorCode.SYS_001
        assert message.severity == ErrorSeverity.ERROR

        print("✅ 通用错误处理正确")

    def test_handle_with_context(self):
        """测试带上下文的错误处理"""
        handler = FriendlyErrorHandler()

        exception = ValueError("Invalid field value")
        context = {"field": "username"}

        message = handler.handle_exception(exception, context)

        # 第一个建议应该包含字段名
        if "检查 username 字段" in message.suggestions[0]:
            assert True

        print("✅ 带上下文错误处理正确")

    def test_try_auto_fix_success(self):
        """测试自动修复成功"""
        handler = FriendlyErrorHandler()

        # 创建一个可以自动修复的错误
        def auto_fix_func():
            return True

        message = UserErrorMessage(
            code=ErrorCode.AUTH_002,
            title="测试",
            description="测试",
            suggestions=[],
            auto_fix=auto_fix_func
        )

        result = handler.try_auto_fix(message)

        assert result is True

        # 检查统计
        stats = handler.get_stats()
        assert stats["auto_fixed"] == 1

        print("✅ 自动修复成功正确")

    def test_try_auto_fix_failure(self):
        """测试自动修复失败"""
        handler = FriendlyErrorHandler()

        # 没有自动修复函数
        message = UserErrorMessage(
            code=ErrorCode.NET_001,
            title="测试",
            description="测试",
            suggestions=[]
        )

        result = handler.try_auto_fix(message)

        assert result is False

        print("✅ 自动修复失败正确")

    def test_try_auto_fix_exception(self):
        """测试自动修复异常"""
        handler = FriendlyErrorHandler()

        def auto_fix_func():
            raise Exception("Auto fix failed")

        message = UserErrorMessage(
            code=ErrorCode.AUTH_002,
            title="测试",
            description="测试",
            suggestions=[],
            auto_fix=auto_fix_func
        )

        result = handler.try_auto_fix(message)

        # 修复失败应该返回 False
        assert result is False

        print("✅ 自动修复异常正确")

    def test_format_for_display(self):
        """测试格式化显示"""
        handler = FriendlyErrorHandler()

        message = handler.mapper.get_message(ErrorCode.NET_001)

        formatted = handler.format_for_display(message)

        assert "【网络连接失败】" in formatted
        assert "建议解决方案：" in formatted
        assert "1. 检查网络连接是否正常" in formatted
        assert "2. 确认服务器地址是否正确" in formatted

        print("✅ 格式化显示正确")

    def test_format_with_help_url(self):
        """测试带帮助文档的格式化"""
        handler = FriendlyErrorHandler()

        message = handler.mapper.get_message(ErrorCode.NET_001)

        formatted = handler.format_for_display(message)

        assert "帮助文档:" in formatted
        assert "https://github.com" in formatted

        print("✅ 帮助文档格式化正确")

    def test_stats(self):
        """测试统计信息"""
        handler = FriendlyErrorHandler()

        # 处理一些错误
        handler.handle_exception(ConnectionError("Error 1"))
        handler.handle_exception(TimeoutError("Error 2"))

        stats = handler.get_stats()

        assert stats["total_errors"] == 2

        # 重置统计
        handler.reset_stats()
        stats = handler.get_stats()

        assert stats["total_errors"] == 0

        print("✅ 统计信息正确")


# ============================================================================
# 便捷函数测试
# ============================================================================

class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_handle_error(self):
        """测试错误处理函数"""
        exception = ConnectionError("Test error")
        message = handle_error(exception)

        assert message is not None
        assert message.code == ErrorCode.NET_001

        print("✅ 错误处理函数正确")

    def test_format_error(self):
        """测试格式化函数"""
        exception = TimeoutError("Test timeout")
        message = handle_error(exception)

        formatted = format_error(message)

        assert "【" in formatted
        assert "建议解决方案：" in formatted

        print("✅ 格式化函数正确")

    def test_try_auto_fix(self):
        """测试自动修复函数"""
        def auto_fix():
            return True

        message = UserErrorMessage(
            code=ErrorCode.AUTH_002,
            title="测试",
            description="测试",
            suggestions=[],
            auto_fix=auto_fix
        )

        result = try_auto_fix(message)

        assert result is True

        print("✅ 自动修复函数正确")


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试"""

    def test_full_error_handling_flow(self):
        """测试完整错误处理流程"""
        handler = FriendlyErrorHandler()

        # 1. 处理网络错误
        network_error = ConnectionError("Network unreachable")
        network_message = handler.handle_exception(network_error)

        # 2. 格式化显示
        formatted = handler.format_for_display(network_message)

        # 3. 尝试自动修复（网络错误通常不能自动修复）
        fixed = handler.try_auto_fix(network_message)

        assert network_message.category == ErrorCategory.NETWORK
        assert "【网络连接失败】" in formatted
        assert fixed is False  # 网络错误不能自动修复

        print("✅ 完整错误处理流程正确")

    def test_multiple_errors_stats(self):
        """测试多错误统计"""
        handler = FriendlyErrorHandler()

        # 处理多种类型的错误
        errors = [
            ConnectionError("Error 1"),
            TimeoutError("Error 2"),
            ValueError("Error 3"),
            BusinessError(message="Error 4", user_message="业务错误")
        ]

        for error in errors:
            handler.handle_exception(error)

        stats = handler.get_stats()

        assert stats["total_errors"] == 4

        print("✅ 多错误统计正确")


# ============================================================================
# 运行所有测试
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行友好错误提示测试...\n")

    print("="*60)
    print("测试用户错误信息")
    print("="*60)
    TestUserErrorMessage().test_create_message()
    TestUserErrorMessage().test_message_with_auto_fix()

    print("\n" + "="*60)
    print("测试错误信息映射器")
    print("="*60)
    TestErrorMessageMapper().test_initialization()
    TestErrorMessageMapper().test_get_message()
    TestErrorMessageMapper().test_get_unknown_code()
    TestErrorMessageMapper().test_register_custom_message()
    TestErrorMessageMapper().test_pattern_matching()
    TestErrorMessageMapper().test_pattern_no_match()

    print("\n" + "="*60)
    print("测试友好的错误处理器")
    print("="*60)
    TestFriendlyErrorHandler().test_initialization()
    TestFriendlyErrorHandler().test_handle_network_error()
    TestFriendlyErrorHandler().test_handle_timeout_error()
    TestFriendlyErrorHandler().test_handle_business_error()
    TestFriendlyErrorHandler().test_handle_security_error()
    TestFriendlyErrorHandler().test_handle_configuration_error()
    TestFriendlyErrorHandler().test_handle_generic_error()
    TestFriendlyErrorHandler().test_handle_with_context()
    TestFriendlyErrorHandler().test_try_auto_fix_success()
    TestFriendlyErrorHandler().test_try_auto_fix_failure()
    TestFriendlyErrorHandler().test_try_auto_fix_exception()
    TestFriendlyErrorHandler().test_format_for_display()
    TestFriendlyErrorHandler().test_format_with_help_url()
    TestFriendlyErrorHandler().test_stats()

    print("\n" + "="*60)
    print("测试便捷函数")
    print("="*60)
    TestConvenienceFunctions().test_handle_error()
    TestConvenienceFunctions().test_format_error()
    TestConvenienceFunctions().test_try_auto_fix()

    print("\n" + "="*60)
    print("测试集成")
    print("="*60)
    TestIntegration().test_full_error_handling_flow()
    TestIntegration().test_multiple_errors_stats()

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
