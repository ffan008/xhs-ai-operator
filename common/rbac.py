"""
基于角色的访问控制 (RBAC) 模块

提供角色定义、权限检查和访问控制功能。
"""

from typing import Dict, List, Set, Optional, Callable, Any
from enum import Enum
from functools import wraps
from .auth import AuthContext
from .exceptions import AuthorizationError, AuthenticationError


# ============================================================================
# 角色定义
# ============================================================================

class Role(str, Enum):
    """系统角色枚举"""

    # 超级管理员（所有权限）
    ADMIN = "admin"

    # 运营人员（发布、编辑）
    OPERATOR = "operator"

    # 分析师（只读数据访问）
    ANALYST = "analyst"

    # 访客（最小权限）
    GUEST = "guest"


# ============================================================================
# 权限定义
# ============================================================================

class Permission(str, Enum):
    """系统权限枚举"""

    # 笔记相关
    NOTE_CREATE = "note:create"
    NOTE_READ = "note:read"
    NOTE_UPDATE = "note:update"
    NOTE_DELETE = "note:delete"
    NOTE_PUBLISH = "note:publish"

    # 账号相关
    ACCOUNT_READ = "account:read"
    ACCOUNT_UPDATE = "account:update"
    ACCOUNT_DELETE = "account:delete"

    # 数据相关
    DATA_READ = "data:read"
    DATA_EXPORT = "data:export"

    # 调度相关
    SCHEDULE_READ = "schedule:read"
    SCHEDULE_CREATE = "schedule:create"
    SCHEDULE_UPDATE = "schedule:update"
    SCHEDULE_DELETE = "schedule:delete"

    # 系统相关
    SYSTEM_CONFIG = "system:config"
    SYSTEM_ADMIN = "system:admin"

    # API 相关
    API_CALL = "api:call"
    API_MANAGE = "api:manage"


# ============================================================================
# 角色权限映射
# ============================================================================

# 默认角色权限映射
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # 管理员拥有所有权限
        Permission.NOTE_CREATE,
        Permission.NOTE_READ,
        Permission.NOTE_UPDATE,
        Permission.NOTE_DELETE,
        Permission.NOTE_PUBLISH,
        Permission.ACCOUNT_READ,
        Permission.ACCOUNT_UPDATE,
        Permission.ACCOUNT_DELETE,
        Permission.DATA_READ,
        Permission.DATA_EXPORT,
        Permission.SCHEDULE_READ,
        Permission.SCHEDULE_CREATE,
        Permission.SCHEDULE_UPDATE,
        Permission.SCHEDULE_DELETE,
        Permission.SYSTEM_CONFIG,
        Permission.SYSTEM_ADMIN,
        Permission.API_CALL,
        Permission.API_MANAGE,
    },

    Role.OPERATOR: {
        # 运营人员权限
        Permission.NOTE_CREATE,
        Permission.NOTE_READ,
        Permission.NOTE_UPDATE,
        Permission.NOTE_PUBLISH,
        Permission.ACCOUNT_READ,
        Permission.DATA_READ,
        Permission.SCHEDULE_READ,
        Permission.SCHEDULE_CREATE,
        Permission.SCHEDULE_UPDATE,
        Permission.API_CALL,
    },

    Role.ANALYST: {
        # 分析师权限（只读）
        Permission.NOTE_READ,
        Permission.ACCOUNT_READ,
        Permission.DATA_READ,
        Permission.DATA_EXPORT,
        Permission.SCHEDULE_READ,
    },

    Role.GUEST: {
        # 访客权限（最小）
        Permission.NOTE_READ,
        Permission.DATA_READ,
    },
}


# ============================================================================
# 资源定义
# ============================================================================

class Resource(str, Enum):
    """系统资源枚举"""

    NOTE = "note"
    ACCOUNT = "account"
    DATA = "data"
    SCHEDULE = "schedule"
    SYSTEM = "system"
    API = "api"


# ============================================================================
# 操作定义
# ============================================================================

class Action(str, Enum):
    """系统操作枚举"""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    PUBLISH = "publish"
    EXPORT = "export"
    MANAGE = "manage"


# ============================================================================
# RBAC 管理器
# ============================================================================

class RBACManager:
    """RBAC 管理器"""

    def __init__(self):
        """初始化 RBAC 管理器"""
        # 自定义角色权限映射（允许运行时修改）
        self.custom_role_permissions: Dict[str, Set[str]] = {}

        # 用户角色映射（用户 ID -> 角色列表）
        self.user_roles: Dict[str, List[Role]] = {}

        # 用户额外权限（用户 ID -> 额外权限列表）
        self.user_permissions: Dict[str, Set[Permission]] = {}

    def get_role_permissions(self, role: str) -> Set[Permission]:
        """
        获取角色的权限

        Args:
            role: 角色名

        Returns:
            权限集合
        """
        # 检查是否是枚举角色
        try:
            enum_role = Role(role)
            return ROLE_PERMISSIONS.get(enum_role, set())
        except ValueError:
            # 自定义角色
            return set(self.custom_role_permissions.get(role, set()))

    def get_user_roles(self, user_id: str) -> List[Role]:
        """
        获取用户的角色

        Args:
            user_id: 用户 ID

        Returns:
            角色列表
        """
        return self.user_roles.get(user_id, [])

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """
        获取用户的所有权限（包括角色权限和额外权限）

        Args:
            user_id: 用户 ID

        Returns:
            权限集合
        """
        permissions = set()

        # 添加角色权限
        for role in self.get_user_roles(user_id):
            permissions.update(self.get_role_permissions(role.value))

        # 添加用户额外权限
        if user_id in self.user_permissions:
            permissions.update(self.user_permissions[user_id])

        return permissions

    def assign_role(self, user_id: str, role: Role) -> None:
        """
        为用户分配角色

        Args:
            user_id: 用户 ID
            role: 角色
        """
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []

        if role not in self.user_roles[user_id]:
            self.user_roles[user_id].append(role)

    def remove_role(self, user_id: str, role: Role) -> None:
        """
        移除用户的角色

        Args:
            user_id: 用户 ID
            role: 角色
        """
        if user_id in self.user_roles:
            if role in self.user_roles[user_id]:
                self.user_roles[user_id].remove(role)

    def grant_permission(self, user_id: str, permission: Permission) -> None:
        """
        为用户授予权限

        Args:
            user_id: 用户 ID
            permission: 权限
        """
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = set()

        self.user_permissions[user_id].add(permission)

    def revoke_permission(self, user_id: str, permission: Permission) -> None:
        """
        撤销用户的权限

        Args:
            user_id: 用户 ID
            permission: 权限
        """
        if user_id in self.user_permissions:
            self.user_permissions[user_id].discard(permission)

    def check_permission(
        self,
        user_id: str,
        permission: Permission
    ) -> bool:
        """
        检查用户是否有权限

        Args:
            user_id: 用户 ID
            permission: 权限

        Returns:
            是否有权限
        """
        return permission in self.get_user_permissions(user_id)

    def check_any_permission(
        self,
        user_id: str,
        permissions: List[Permission]
    ) -> bool:
        """
        检查用户是否有任意一个权限

        Args:
            user_id: 用户 ID
            permissions: 权限列表

        Returns:
            是否有任意一个权限
        """
        user_permissions = self.get_user_permissions(user_id)
        return any(perm in user_permissions for perm in permissions)

    def check_all_permissions(
        self,
        user_id: str,
        permissions: List[Permission]
    ) -> bool:
        """
        检查用户是否有所有权限

        Args:
            user_id: 用户 ID
            permissions: 权限列表

        Returns:
            是否有所有权限
        """
        user_permissions = self.get_user_permissions(user_id)
        return all(perm in user_permissions for perm in permissions)

    def require_permission(self, permission: Permission) -> Callable:
        """
        权限检查装饰器

        Args:
            permission: 需要的权限

        Returns:
            装饰器函数

        Example:
            @rbac.require_permission(Permission.NOTE_PUBLISH)
            def publish_note():
                pass
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(auth_context: AuthContext, *args, **kwargs):
                if not auth_context.has_permission(permission):
                    raise AuthorizationError(
                        resource=permission.value.split(":")[0],
                        action=permission.value.split(":")[1]
                    )
                return func(auth_context, *args, **kwargs)

            return wrapper

        return decorator

    def require_role(self, role: Role) -> Callable:
        """
        角色检查装饰器

        Args:
            role: 需要的角色

        Returns:
            装饰器函数

        Example:
            @rbac.require_role(Role.ADMIN)
            def admin_function():
                pass
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(auth_context: AuthContext, *args, **kwargs):
                if not auth_context.has_role(role.value):
                    raise AuthorizationError(
                        resource="system",
                        action=f"requires role {role.value}"
                    )
                return func(auth_context, *args, **kwargs)

            return wrapper

        return decorator

    def require_any_role(self, roles: List[Role]) -> Callable:
        """
        任意角色检查装饰器

        Args:
            roles: 角色列表

        Returns:
            装饰器函数
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(auth_context: AuthContext, *args, **kwargs):
                if not auth_context.has_any_role([r.value for r in roles]):
                    raise AuthorizationError(
                        resource="system",
                        action=f"requires one of roles: {[r.value for r in roles]}"
                    )
                return func(auth_context, *args, **kwargs)

            return wrapper

        return decorator


# ============================================================================
# 全局 RBAC 实例
# ============================================================================

# 默认 RBAC 管理器
default_rbac = RBACManager()


# ============================================================================
# 便捷函数
# ============================================================================

def check_permission(
    auth_context: AuthContext,
    permission: Permission
) -> bool:
    """
    检查认证上下文是否有权限

    Args:
        auth_context: 认证上下文
        permission: 权限

    Returns:
        是否有权限
    """
    return auth_context.has_permission(permission)


def require_permission(permission: Permission) -> Callable:
    """
    权限检查装饰器（使用全局 RBAC 管理器）

    Args:
        permission: 需要的权限

    Returns:
        装饰器函数

    Example:
        @require_permission(Permission.NOTE_PUBLISH)
        def publish_note(auth_context: AuthContext):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(auth_context: AuthContext, *args, **kwargs):
            if not auth_context.has_permission(permission):
                raise AuthorizationError(
                    resource=permission.value.split(":")[0],
                    action=permission.value.split(":")[1]
                )
            return func(auth_context, *args, **kwargs)

        return wrapper

    return decorator


def require_role(role: Role) -> Callable:
    """
    角色检查装饰器（使用全局 RBAC 管理器）

    Args:
        role: 需要的角色

    Returns:
        装饰器函数

    Example:
        @require_role(Role.ADMIN)
        def admin_function(auth_context: AuthContext):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(auth_context: AuthContext, *args, **kwargs):
            if not auth_context.has_role(role.value):
                raise AuthorizationError(
                    resource="system",
                    action=f"requires role {role.value}"
                )
            return func(auth_context, *args, **kwargs)

        return wrapper

    return decorator
