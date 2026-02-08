"""
用户友好的错误提示模块

将技术错误转换为用户友好的提示，提供解决建议。
"""

import re
from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, field
from enum import Enum

from .exceptions import BaseError, BusinessError, ConfigurationError, SecurityError


# ============================================================================
# 错误严重程度
# ============================================================================

class ErrorSeverity(str, Enum):
    """错误严重程度"""
    INFO = "info"           # 信息提示
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 严重错误


# ============================================================================
# 错误类别
# ============================================================================

class ErrorCategory(str, Enum):
    """错误类别"""
    NETWORK = "network"           # 网络错误
    API = "api"                   # API 错误
    AUTH = "auth"                 # 认证错误
    CONFIG = "config"             # 配置错误
    DATA = "data"                 # 数据错误
    PERMISSION = "permission"     # 权限错误
    RATE_LIMIT = "rate_limit"     # 限流错误
    VALIDATION = "validation"     # 验证错误
    SYSTEM = "system"             # 系统错误


# ============================================================================
# 错误码
# ============================================================================

class ErrorCode(str, Enum):
    """错误码"""
    # 网络错误
    NET_001 = "NET_001"  # 网络连接失败
    NET_002 = "NET_002"  # 请求超时
    NET_003 = "NET_003"  # DNS 解析失败
    NET_004 = "NET_004"  # 连接被拒绝

    # API 错误
    API_001 = "API_001"  # API 调用失败
    API_002 = "API_002"  # API 返回错误
    API_003 = "API_003"  # API 限流
    API_004 = "API_004"  # API 密钥无效
    API_005 = "API_005"  # API 服务不可用

    # 认证错误
    AUTH_001 = "AUTH_001"  # 登录失败
    AUTH_002 = "AUTH_002"  # Token 过期
    AUTH_003 = "AUTH_003"  # Token 无效
    AUTH_004 = "AUTH_004"  # 权限不足

    # 配置错误
    CFG_001 = "CFG_001"  # 配置文件缺失
    CFG_002 = "CFG_002"  # 配置格式错误
    CFG_003 = "CFG_003"  # 必填项缺失
    CFG_004 = "CFG_004"  # 配置值无效

    # 数据错误
    DATA_001 = "DATA_001"  # 数据不存在
    DATA_002 = "DATA_002"  # 数据格式错误
    DATA_003 = "DATA_003"  # 数据验证失败
    DATA_004 = "DATA_004"  # 数据重复

    # 权限错误
    PERM_001 = "PERM_001"  # 权限不足
    PERM_002 = "PERM_002"  # 账号被禁用
    PERM_003 = "PERM_003"  # 操作不被允许

    # 验证错误
    VAL_001 = "VAL_001"  # 输入为空
    VAL_002 = "VAL_002"  # 格式不正确
    VAL_003 = "VAL_003"  # 长度超限
    VAL_004 = "VAL_004"  # 值超出范围

    # 系统错误
    SYS_001 = "SYS_001"  # 系统错误
    SYS_002 = "SYS_002"  # 资源不足
    SYS_003 = "SYS_003"  # 服务不可用


# ============================================================================
# 用户友好的错误信息
# ============================================================================

@dataclass
class UserErrorMessage:
    """用户错误信息"""
    code: ErrorCode
    title: str
    description: str
    suggestions: List[str]
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: ErrorCategory = ErrorCategory.SYSTEM
    auto_fix: Optional[Callable[[], bool]] = None
    help_url: Optional[str] = None
    technical_details: Optional[str] = None


# ============================================================================
# 错误信息映射
# ============================================================================

class ErrorMessageMapper:
    """错误信息映射器"""

    def __init__(self):
        """初始化映射器"""
        self._error_map: Dict[ErrorCode, UserErrorMessage] = {}
        self._pattern_map: List[tuple] = []
        self._init_default_messages()

    def _init_default_messages(self) -> None:
        """初始化默认错误信息"""
        # 网络错误
        self._error_map[ErrorCode.NET_001] = UserErrorMessage(
            code=ErrorCode.NET_001,
            title="网络连接失败",
            description="无法连接到服务器，请检查网络连接",
            suggestions=[
                "检查网络连接是否正常",
                "确认服务器地址是否正确",
                "尝试关闭防火墙或代理",
                "稍后重试"
            ],
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.NETWORK,
            help_url="https://github.com/ffan008/xhs-ai-operator/wiki/network-issues"
        )

        self._error_map[ErrorCode.NET_002] = UserErrorMessage(
            code=ErrorCode.NET_002,
            title="请求超时",
            description="请求服务器超时，请稍后重试",
            suggestions=[
                "检查网络连接是否稳定",
                "稍后重试",
                "如果是频繁超时，可能是服务器负载过高"
            ],
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.NETWORK,
            help_url="https://github.com/ffan008/xhs-ai-operator/wiki/timeout-issues"
        )

        self._error_map[ErrorCode.NET_003] = UserErrorMessage(
            code=ErrorCode.NET_003,
            title="DNS 解析失败",
            description="无法解析服务器地址",
            suggestions=[
                "检查域名是否正确",
                "尝试使用 IP 地址",
                "检查 DNS 服务器设置",
                "刷新 DNS 缓存"
            ],
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.NETWORK
        )

        # API 错误
        self._error_map[ErrorCode.API_001] = UserErrorMessage(
            code=ErrorCode.API_001,
            title="API 调用失败",
            description="调用外部 API 时发生错误",
            suggestions=[
                "检查 API 密钥是否正确",
                "确认 API 服务是否可用",
                "稍后重试",
                "查看 API 文档"
            ],
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.API
        )

        self._error_map[ErrorCode.API_003] = UserErrorMessage(
            code=ErrorCode.API_003,
            title="API 请求频率超限",
            description="请求过于频繁，已被限流",
            suggestions=[
                "降低请求频率",
                "等待一段时间后重试",
                "升级 API 套餐以获得更高的限额"
            ],
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.RATE_LIMIT,
            help_url="https://github.com/ffan008/xhs-ai-operator/wiki/rate-limits"
        )

        self._error_map[ErrorCode.API_004] = UserErrorMessage(
            code=ErrorCode.API_004,
            title="API 密钥无效",
            description="API 密钥不正确或已过期",
            suggestions=[
                "检查 API 密钥是否正确",
                "重新生成 API 密钥",
                "更新配置文件中的密钥"
            ],
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.API
        )

        # 认证错误
        self._error_map[ErrorCode.AUTH_001] = UserErrorMessage(
            code=ErrorCode.AUTH_001,
            title="登录失败",
            description="用户名或密码错误",
            suggestions=[
                "检查用户名是否正确",
                "确认密码是否正确",
                "检查是否启用了大小写锁定",
                "尝试重置密码"
            ],
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.AUTH
        )

        self._error_map[ErrorCode.AUTH_002] = UserErrorMessage(
            code=ErrorCode.AUTH_002,
            title="登录已过期",
            description="您的登录已过期，需要重新登录",
            suggestions=[
                "重新登录系统",
                "如果频繁过期，检查系统时间是否正确"
            ],
            severity=ErrorSeverity.INFO,
            category=ErrorCategory.AUTH,
            auto_fix=lambda: True  # 可以自动重新登录
        )

        self._error_map[ErrorCode.AUTH_004] = UserErrorMessage(
            code=ErrorCode.AUTH_004,
            title="权限不足",
            description="您没有执行此操作的权限",
            suggestions=[
                "确认您已登录",
                "联系管理员申请权限",
                "检查账号是否被禁用"
            ],
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.PERMISSION
        )

        # 配置错误
        self._error_map[ErrorCode.CFG_001] = UserErrorMessage(
            code=ErrorCode.CFG_001,
            title="配置文件缺失",
            description="找不到必需的配置文件",
            suggestions=[
                "运行配置向导: python3 scripts/setup_wizard.py",
                "检查配置文件路径",
                "查看示例配置文件"
            ],
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.CONFIG,
            help_url="https://github.com/ffan008/xhs-ai-operator/wiki/configuration"
        )

        self._error_map[ErrorCode.CFG_003] = UserErrorMessage(
            code=ErrorCode.CFG_003,
            title="必填配置项缺失",
            description="配置文件中缺少必需的配置项",
            suggestions=[
                "运行配置向导生成完整配置",
                "检查配置文件中的必填项",
                "参考配置文件模板"
            ],
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.CONFIG
        )

        self._error_map[ErrorCode.CFG_004] = UserErrorMessage(
            code=ErrorCode.CFG_004,
            title="配置值无效",
            description="配置文件中的值不符合要求",
            suggestions=[
                "检查配置值的格式",
                "查看配置文档了解正确格式",
                "运行配置验证工具"
            ],
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.CONFIG
        )

        # 数据错误
        self._error_map[ErrorCode.DATA_001] = UserErrorMessage(
            code=ErrorCode.DATA_001,
            title="数据不存在",
            description="请求的数据不存在",
            suggestions=[
                "检查数据 ID 是否正确",
                "确认数据是否已被删除",
                "刷新数据列表"
            ],
            severity=ErrorSeverity.INFO,
            category=ErrorCategory.DATA
        )

        self._error_map[ErrorCode.DATA_003] = UserErrorMessage(
            code=ErrorCode.DATA_003,
            title="数据验证失败",
            description="提交的数据不符合要求",
            suggestions=[
                "检查数据格式是否正确",
                "确认必填项都已填写",
                "查看数据验证规则"
            ],
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.VALIDATION
        )

        # 验证错误
        self._error_map[ErrorCode.VAL_001] = UserErrorMessage(
            code=ErrorCode.VAL_001,
            title="输入不能为空",
            description="此项为必填项，请输入内容",
            suggestions=[
                "请填写此项",
                "检查是否有遗漏"
            ],
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION
        )

        self._error_map[ErrorCode.VAL_002] = UserErrorMessage(
            code=ErrorCode.VAL_002,
            title="格式不正确",
            description="输入的格式不符合要求",
            suggestions=[
                "检查输入格式",
                "查看格式说明",
                "参考示例"
            ],
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION
        )

        self._error_map[ErrorCode.VAL_003] = UserErrorMessage(
            code=ErrorCode.VAL_003,
            title="输入过长",
            description="输入的内容超过了允许的长度",
            suggestions=[
                "精简输入内容",
                "查看长度限制",
                "分段提交"
            ],
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION
        )

        # 系统错误
        self._error_map[ErrorCode.SYS_001] = UserErrorMessage(
            code=ErrorCode.SYS_001,
            title="系统错误",
            description="系统发生未知错误",
            suggestions=[
                "稍后重试",
                "如果问题持续，请联系技术支持",
                "查看系统日志"
            ],
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SYSTEM,
            help_url="https://github.com/ffan008/xhs-ai-operator/issues"
        )

        self._error_map[ErrorCode.SYS_002] = UserErrorMessage(
            code=ErrorCode.SYS_002,
            title="资源不足",
            description="系统资源（内存/磁盘）不足",
            suggestions=[
                "关闭其他应用程序",
                "清理磁盘空间",
                "增加系统资源"
            ],
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SYSTEM
        )

    def get_message(self, code: ErrorCode) -> UserErrorMessage:
        """
        获取错误信息

        Args:
            code: 错误码

        Returns:
            用户错误信息
        """
        return self._error_map.get(code, self._get_default_message(code))

    def _get_default_message(self, code: ErrorCode) -> UserErrorMessage:
        """获取默认错误信息"""
        return UserErrorMessage(
            code=code,
            title="未知错误",
            description=f"发生未知错误: {code.value}",
            suggestions=["稍后重试", "如果问题持续，请联系技术支持"],
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.SYSTEM,
            help_url="https://github.com/ffan008/xhs-ai-operator/issues"
        )

    def add_pattern(self, pattern: str, message: UserErrorMessage) -> None:
        """
        添加错误模式匹配

        Args:
            pattern: 正则表达式模式
            message: 匹配时的错误信息
        """
        self._pattern_map.append((re.compile(pattern), message))

    def match_pattern(self, error_text: str) -> Optional[UserErrorMessage]:
        """
        匹配错误模式

        Args:
            error_text: 错误文本

        Returns:
            匹配的错误信息（如果找到）
        """
        for pattern, message in self._pattern_map:
            if pattern.search(error_text):
                return message
        return None

    def register_custom_message(
        self,
        code: ErrorCode,
        title: str,
        description: str,
        suggestions: List[str],
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        auto_fix: Optional[Callable[[], bool]] = None,
        help_url: Optional[str] = None
    ) -> None:
        """
        注册自定义错误信息

        Args:
            code: 错误码
            title: 标题
            description: 描述
            suggestions: 解决建议列表
            severity: 严重程度
            category: 错误类别
            auto_fix: 自动修复函数
            help_url: 帮助文档 URL
        """
        self._error_map[code] = UserErrorMessage(
            code=code,
            title=title,
            description=description,
            suggestions=suggestions,
            severity=severity,
            category=category,
            auto_fix=auto_fix,
            help_url=help_url
        )


# ============================================================================
# 友好的错误处理器
# ============================================================================

class FriendlyErrorHandler:
    """友好的错误处理器"""

    def __init__(self, mapper: Optional[ErrorMessageMapper] = None):
        """
        初始化错误处理器

        Args:
            mapper: 错误信息映射器
        """
        self.mapper = mapper or ErrorMessageMapper()
        self._stats = {
            "total_errors": 0,
            "auto_fixed": 0,
            "error_categories": {}
        }

    def handle_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> UserErrorMessage:
        """
        处理异常，返回用户友好的错误信息

        Args:
            exception: 异常对象
            context: 额外上下文信息

        Returns:
            用户错误信息
        """
        self._stats["total_errors"] += 1

        # 从异常中提取错误信息
        error_text = str(exception)

        # 尝试模式匹配
        matched_message = self.mapper.match_pattern(error_text)
        if matched_message:
            return self._update_with_context(matched_message, context)

        # 根据异常类型映射
        if isinstance(exception, BaseError):
            return self._handle_base_error(exception, context)
        elif isinstance(exception, ConnectionError):
            return self.mapper.get_message(ErrorCode.NET_001)
        elif isinstance(exception, TimeoutError):
            return self.mapper.get_message(ErrorCode.NET_002)
        else:
            # 默认系统错误
            return self._get_generic_error(error_text, context)

    def _handle_base_error(
        self,
        error: BaseError,
        context: Optional[Dict[str, Any]]
    ) -> UserErrorMessage:
        """处理基础错误"""
        # 根据 BusinessError 的用户消息生成友好提示
        if isinstance(error, BusinessError):
            return UserErrorMessage(
                code=ErrorCode.VAL_002,
                title=error.user_message or "操作失败",
                description=error.user_message or error.message,
                suggestions=[
                    "检查输入是否正确",
                    "查看错误详情",
                    "稍后重试"
                ],
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.VALIDATION,
                technical_details=error.message
            )
        elif isinstance(error, ConfigurationError):
            return self.mapper.get_message(ErrorCode.CFG_004)
        elif isinstance(error, SecurityError):
            return UserErrorMessage(
                code=ErrorCode.AUTH_004,
                title="权限不足",
                description=error.user_message or "您没有执行此操作的权限",
                suggestions=[
                    "确认您已登录",
                    "联系管理员申请权限"
                ],
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.PERMISSION
            )
        else:
            return self._get_generic_error(error.message, context)

    def _get_generic_error(
        self,
        error_text: str,
        context: Optional[Dict[str, Any]]
    ) -> UserErrorMessage:
        """获取通用错误信息"""
        return UserErrorMessage(
            code=ErrorCode.SYS_001,
            title="操作失败",
            description=error_text or "系统发生未知错误",
            suggestions=[
                "稍后重试",
                "检查输入是否正确",
                "如果问题持续，请联系技术支持"
            ],
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.SYSTEM,
            technical_details=error_text
        )

    def _update_with_context(
        self,
        message: UserErrorMessage,
        context: Optional[Dict[str, Any]]
    ) -> UserErrorMessage:
        """使用上下文信息更新错误"""
        if not context:
            return message

        # 根据上下文添加额外建议
        if "field" in context:
            field = context["field"]
            if f"检查 {field} 字段" not in message.suggestions[0]:
                message.suggestions.insert(0, f"检查 {field} 字段")

        return message

    def try_auto_fix(self, message: UserErrorMessage) -> bool:
        """
        尝试自动修复错误

        Args:
            message: 错误信息

        Returns:
            是否修复成功
        """
        if message.auto_fix is None:
            return False

        try:
            result = message.auto_fix()
            if result:
                self._stats["auto_fixed"] += 1
                return True
        except Exception:
            pass

        return False

    def format_for_display(self, message: UserErrorMessage) -> str:
        """
        格式化错误信息用于显示

        Args:
            message: 错误信息

        Returns:
            格式化的文本
        """
        lines = []
        lines.append(f"【{message.title}】")
        lines.append(f"  {message.description}")
        lines.append("")
        lines.append("建议解决方案：")
        for i, suggestion in enumerate(message.suggestions, 1):
            lines.append(f"  {i}. {suggestion}")

        if message.help_url:
            lines.append("")
            lines.append(f"帮助文档: {message.help_url}")

        if message.technical_details:
            lines.append("")
            lines.append(f"技术详情: {message.technical_details}")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_errors": 0,
            "auto_fixed": 0,
            "error_categories": {}
        }


# ============================================================================
# 全局实例
# ============================================================================

# 默认错误处理器
default_error_handler = FriendlyErrorHandler()


# ============================================================================
# 便捷函数
# ============================================================================

def handle_error(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None
) -> UserErrorMessage:
    """
    处理异常（使用默认处理器）

    Args:
        exception: 异常对象
        context: 额外上下文

    Returns:
        用户错误信息
    """
    return default_error_handler.handle_exception(exception, context)


def format_error(message: UserErrorMessage) -> str:
    """
    格式化错误信息用于显示（使用默认处理器）

    Args:
        message: 错误信息

    Returns:
        格式化的文本
    """
    return default_error_handler.format_for_display(message)


def try_auto_fix(message: UserErrorMessage) -> bool:
    """
    尝试自动修复错误（使用默认处理器）

    Args:
        message: 错误信息

    Returns:
        是否修复成功
    """
    return default_error_handler.try_auto_fix(message)
