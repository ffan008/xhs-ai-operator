"""
审计日志模块

记录所有敏感操作，用于安全审计和合规检查。
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from enum import Enum
from threading import Lock

from .auth import AuthContext


# ============================================================================
# 操作类型
# ============================================================================

class AuditAction(str, Enum):
    """审计操作类型"""

    # 认证相关
    LOGIN = "login"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"

    # 笔记相关
    NOTE_CREATE = "note_create"
    NOTE_READ = "note_read"
    NOTE_UPDATE = "note_update"
    NOTE_DELETE = "note_delete"
    NOTE_PUBLISH = "note_publish"

    # 账号相关
    ACCOUNT_CREATE = "account_create"
    ACCOUNT_READ = "account_read"
    ACCOUNT_UPDATE = "account_update"
    ACCOUNT_DELETE = "account_delete"
    ACCOUNT_SWITCH = "account_switch"

    # 数据相关
    DATA_EXPORT = "data_export"
    DATA_ANALYZE = "data_analyze"

    # 调度相关
    SCHEDULE_CREATE = "schedule_create"
    SCHEDULE_UPDATE = "schedule_update"
    SCHEDULE_DELETE = "schedule_delete"

    # 系统相关
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"

    # API 相关
    API_CALL = "api_call"
    API_ERROR = "api_error"

    # 安全相关
    SECURITY_ALERT = "security_alert"
    PERMISSION_DENIED = "permission_denied"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


# ============================================================================
# 审计事件
# ============================================================================

class AuditEvent:
    """审计事件"""

    def __init__(
        self,
        action: AuditAction,
        user_id: str,
        account_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        初始化审计事件

        Args:
            action: 操作类型
            user_id: 用户 ID
            account_id: 账号 ID
            resource_type: 资源类型
            resource_id: 资源 ID
            status: 操作状态（success/failure）
            details: 详细信息
            ip_address: IP 地址
            user_agent: 用户代理
        """
        self.timestamp = datetime.utcnow()
        self.action = action
        self.user_id = user_id
        self.account_id = account_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.status = status
        self.details = details or {}
        self.ip_address = ip_address
        self.user_agent = user_agent

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            字典表示
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "status": self.status,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent
        }

    def to_json(self) -> str:
        """
        转换为 JSON

        Returns:
            JSON 字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ============================================================================
# 审计日志存储
# ============================================================================

class AuditLogStore:
    """审计日志存储"""

    def __init__(self, log_dir: Optional[Path] = None):
        """
        初始化审计日志存储

        Args:
            log_dir: 日志目录（如果为 None，使用默认目录）
        """
        self.log_dir = log_dir or Path("logs/audit")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()

        # 配置日志记录器
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # 文件处理器
        log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setLevel(logging.INFO)

        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def log_event(self, event: AuditEvent) -> None:
        """
        记录审计事件

        Args:
            event: 审计事件
        """
        with self.lock:
            # 记录到日志文件
            self.logger.info(event.to_json())

    def query_events(
        self,
        user_id: Optional[str] = None,
        account_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询审计事件

        Args:
            user_id: 用户 ID
            account_id: 账号 ID
            action: 操作类型
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大返回数量

        Returns:
            审计事件列表
        """
        # TODO: 实现从日志文件查询
        # 当前仅返回空列表
        return []


# ============================================================================
# 审计日志管理器
# ============================================================================

class AuditLogger:
    """审计日志管理器"""

    def __init__(self, store: Optional[AuditLogStore] = None):
        """
        初始化审计日志管理器

        Args:
            store: 审计日志存储（如果为 None，使用默认存储）
        """
        self.store = store or AuditLogStore()

    def log_action(
        self,
        action: AuditAction,
        auth_context: AuthContext,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        记录操作

        Args:
            action: 操作类型
            auth_context: 认证上下文
            resource_type: 资源类型
            resource_id: 资源 ID
            status: 操作状态
            details: 详细信息
            ip_address: IP 地址
            user_agent: 用户代理
        """
        event = AuditEvent(
            action=action,
            user_id=auth_context.user_id,
            account_id=auth_context.account_id,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.store.log_event(event)

    def log_login(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        success: bool = True,
        ip_address: Optional[str] = None
    ) -> None:
        """
        记录登录

        Args:
            user_id: 用户 ID
            account_id: 账号 ID
            success: 是否成功
            ip_address: IP 地址
        """
        event = AuditEvent(
            action=AuditAction.LOGIN,
            user_id=user_id,
            account_id=account_id,
            status="success" if success else "failure",
            details={"login_success": success},
            ip_address=ip_address
        )

        self.store.log_event(event)

    def log_logout(
        self,
        user_id: str,
        account_id: Optional[str] = None
    ) -> None:
        """
        记录登出

        Args:
            user_id: 用户 ID
            account_id: 账号 ID
        """
        event = AuditEvent(
            action=AuditAction.LOGOUT,
            user_id=user_id,
            account_id=account_id
        )

        self.store.log_event(event)

    def log_permission_denied(
        self,
        auth_context: AuthContext,
        resource_type: str,
        action: str
    ) -> None:
        """
        记录权限拒绝

        Args:
            auth_context: 认证上下文
            resource_type: 资源类型
            action: 操作
        """
        event = AuditEvent(
            action=AuditAction.PERMISSION_DENIED,
            user_id=auth_context.user_id,
            account_id=auth_context.account_id,
            resource_type=resource_type,
            status="failure",
            details={"attempted_action": action}
        )

        self.store.log_event(event)

    def log_api_call(
        self,
        auth_context: AuthContext,
        api_name: str,
        params: Optional[Dict[str, Any]] = None,
        success: bool = True
    ) -> None:
        """
        记录 API 调用

        Args:
            auth_context: 认证上下文
            api_name: API 名称
            params: 参数（敏感信息会被脱敏）
            success: 是否成功
        """
        # 脱敏参数
        sanitized_params = {}
        if params:
            for key, value in params.items():
                if key.lower() in ['password', 'token', 'api_key', 'secret']:
                    sanitized_params[key] = '[REDACTED]'
                else:
                    sanitized_params[key] = value

        event = AuditEvent(
            action=AuditAction.API_CALL,
            user_id=auth_context.user_id,
            account_id=auth_context.account_id,
            resource_type="api",
            resource_id=api_name,
            status="success" if success else "failure",
            details={"params": sanitized_params}
        )

        self.store.log_event(event)

    def log_security_alert(
        self,
        alert_type: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> None:
        """
        记录安全警报

        Args:
            alert_type: 警报类型
            details: 详细信息
            user_id: 用户 ID（如果适用）
        """
        event = AuditEvent(
            action=AuditAction.SECURITY_ALERT,
            user_id=user_id or "system",
            status="alert",
            details={"alert_type": alert_type, **details}
        )

        self.store.log_event(event)


# ============================================================================
# 全局审计日志实例
# ============================================================================

# 默认审计日志管理器
default_audit_logger = AuditLogger()


# ============================================================================
# 审计装饰器
# ============================================================================

def audit_action(
    action: AuditAction,
    resource_type: Optional[str] = None,
    log_args: bool = False
):
    """
    审计装饰器

    Args:
        action: 操作类型
        resource_type: 资源类型
        log_args: 是否记录参数

    Returns:
        装饰器函数

    Example:
        @audit_action(AuditAction.NOTE_CREATE, resource_type="note")
        def create_note(auth_context: AuthContext, title: str, content: str):
            pass
    """

    def decorator(func):
        def wrapper(auth_context: AuthContext, *args, **kwargs):
            # 执行函数
            try:
                result = func(auth_context, *args, **kwargs)

                # 记录成功
                details = {}
                if log_args:
                    details["args"] = str(args)[:200]  # 限制长度
                    details["kwargs"] = str(kwargs)[:200]

                default_audit_logger.log_action(
                    action=action,
                    auth_context=auth_context,
                    resource_type=resource_type,
                    status="success",
                    details=details
                )

                return result

            except Exception as e:
                # 记录失败
                default_audit_logger.log_action(
                    action=action,
                    auth_context=auth_context,
                    resource_type=resource_type,
                    status="failure",
                    details={"error": str(e)[:200]}
                )

                raise

        return wrapper

    return decorator


# ============================================================================
# 便捷函数
# ============================================================================

def log_login(user_id: str, success: bool = True, ip_address: Optional[str] = None) -> None:
    """记录登录"""
    default_audit_logger.log_login(user_id, success=success, ip_address=ip_address)


def log_logout(user_id: str) -> None:
    """记录登出"""
    default_audit_logger.log_logout(user_id)


def log_permission_denied(auth_context: AuthContext, resource_type: str, action: str) -> None:
    """记录权限拒绝"""
    default_audit_logger.log_permission_denied(auth_context, resource_type, action)


def log_security_alert(alert_type: str, details: Dict[str, Any], user_id: Optional[str] = None) -> None:
    """记录安全警报"""
    default_audit_logger.log_security_alert(alert_type, details, user_id)
