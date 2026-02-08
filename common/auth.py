"""
JWT 令牌认证模块

提供 JWT 令牌的生成、验证和刷新功能。
"""

import jwt
import time
import hashlib
import secrets
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from .exceptions import (
    AuthenticationError,
    SecurityError,
    ConfigurationError
)


# ============================================================================
# JWT 配置
# ============================================================================

class JWTConfig:
    """JWT 配置类"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        issuer: str = "mcp-servers",
        audience: Optional[str] = None
    ):
        """
        初始化 JWT 配置

        Args:
            secret_key: JWT 密钥（如果为 None，则从环境变量或生成）
            algorithm: 加密算法
            access_token_expire_minutes: 访问令牌过期时间（分钟）
            refresh_token_expire_days: 刷新令牌过期时间（天）
            issuer: 发行者
            audience: 受众
        """
        self.secret_key = secret_key or self._get_or_generate_secret()
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.issuer = issuer
        self.audience = audience

    @staticmethod
    def _get_or_generate_secret() -> str:
        """获取或生成 JWT 密钥"""
        import os

        # 尝试从环境变量获取
        secret = os.environ.get("JWT_SECRET_KEY")
        if secret:
            return secret

        # 从文件获取
        secret_file = Path(".jwt_secret")
        if secret_file.exists():
            return secret_file.read_text().strip()

        # 生成新密钥并保存
        secret = secrets.token_urlsafe(32)
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        secret_file.write_text(secret)
        secret_file.chmod(0o600)  # 只有所有者可读写

        return secret


# ============================================================================
# JWT 令牌管理器
# ============================================================================

class JWTManager:
    """JWT 令牌管理器"""

    def __init__(self, config: Optional[JWTConfig] = None):
        """
        初始化 JWT 管理器

        Args:
            config: JWT 配置（如果为 None，使用默认配置）
        """
        self.config = config or JWTConfig()

    def generate_access_token(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成访问令牌

        Args:
            user_id: 用户 ID
            account_id: 账号 ID（用于多账号隔离）
            roles: 角色列表
            permissions: 权限列表
            extra_claims: 额外的声明

        Returns:
            JWT 访问令牌
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.config.access_token_expire_minutes)

        payload = {
            "sub": user_id,  # 主题（用户 ID）
            "iat": now,  # 签发时间
            "exp": expire,  # 过期时间
            "iss": self.config.issuer,  # 发行者
            "type": "access"  # 令牌类型
        }

        # 添加账号 ID（用于多账号隔离）
        if account_id:
            payload["account_id"] = account_id

        # 添加角色
        if roles:
            payload["roles"] = roles

        # 添加权限
        if permissions:
            payload["permissions"] = permissions

        # 添加受众
        if self.config.audience:
            payload["aud"] = self.config.audience

        # 添加额外声明
        if extra_claims:
            payload.update(extra_claims)

        # 生成令牌
        token = jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

        return token

    def generate_refresh_token(
        self,
        user_id: str,
        token_id: Optional[str] = None
    ) -> str:
        """
        生成刷新令牌

        Args:
            user_id: 用户 ID
            token_id: 令牌 ID（用于令牌撤销）

        Returns:
            JWT 刷新令牌
        """
        now = datetime.utcnow()
        expire = now + timedelta(days=self.config.refresh_token_expire_days)

        # 生成唯一的令牌 ID
        if token_id is None:
            token_id = secrets.token_urlsafe(16)

        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expire,
            "iss": self.config.issuer,
            "type": "refresh",
            "jti": token_id  # 令牌 ID
        }

        token = jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

        return token

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        验证并解码令牌

        Args:
            token: JWT 令牌

        Returns:
            解码后的令牌 payload

        Raises:
            AuthenticationError: 令牌无效或过期
        """
        try:
            # 解码并验证令牌
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                options={
                    "require": ["exp", "iat", "iss", "type"],
                    "verify_aud": self.config.audience is not None
                }
            )

            # 检查令牌类型
            token_type = payload.get("type")
            if token_type not in ["access", "refresh"]:
                raise AuthenticationError("Invalid token type")

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """
        验证访问令牌

        Args:
            token: JWT 访问令牌

        Returns:
            解码后的令牌 payload

        Raises:
            AuthenticationError: 令牌无效或过期
        """
        payload = self.verify_token(token)

        # 检查令牌类型
        if payload.get("type") != "access":
            raise AuthenticationError("Expected access token, got refresh token")

        return payload

    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """
        验证刷新令牌

        Args:
            token: JWT 刷新令牌

        Returns:
            解码后的令牌 payload

        Raises:
            AuthenticationError: 令牌无效或过期
        """
        payload = self.verify_token(token)

        # 检查令牌类型
        if payload.get("type") != "refresh":
            raise AuthenticationError("Expected refresh token, got access token")

        return payload

    def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        使用刷新令牌刷新访问令牌

        Args:
            refresh_token: 刷新令牌

        Returns:
            (新的访问令牌, 新的刷新令牌)

        Raises:
            AuthenticationError: 刷新令牌无效或过期
        """
        # 验证刷新令牌
        payload = self.verify_refresh_token(refresh_token)

        # 提取用户信息
        user_id = payload["sub"]
        token_id = payload.get("jti")

        # 生成新的访问令牌
        access_token = self.generate_access_token(
            user_id=user_id,
            account_id=payload.get("account_id"),
            roles=payload.get("roles"),
            permissions=payload.get("permissions")
        )

        # 生成新的刷新令牌
        new_refresh_token = self.generate_refresh_token(user_id=user_id)

        # TODO: 将旧的刷新令牌添加到撤销列表（使用 Redis）

        return access_token, new_refresh_token

    def get_token_info(self, token: str) -> Dict[str, Any]:
        """
        获取令牌信息（不验证签名，仅用于调试）

        Args:
            token: JWT 令牌

        Returns:
            令牌信息
        """
        try:
            # 解码但不验证（仅用于调试）
            payload = jwt.decode(token, options={"verify_signature": False})

            return {
                "user_id": payload.get("sub"),
                "account_id": payload.get("account_id"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "type": payload.get("type")
            }
        except Exception:
            return {"error": "Invalid token format"}


# ============================================================================
# 令牌存储（用于撤销管理）
# ============================================================================

class TokenStore:
    """令牌存储（用于撤销管理）"""

    def __init__(self):
        """初始化令牌存储"""
        # 使用内存存储（生产环境应使用 Redis）
        self._revoked_tokens: Dict[str, float] = {}  # token_id -> revoke_time

    def revoke_token(self, token_id: str, ttl: Optional[int] = None) -> None:
        """
        撤销令牌

        Args:
            token_id: 令牌 ID
            ttl: 生存时间（秒），如果为 None，则使用令牌的过期时间
        """
        self._revoked_tokens[token_id] = time.time()

    def is_token_revoked(self, token_id: str) -> bool:
        """
        检查令牌是否被撤销

        Args:
            token_id: 令牌 ID

        Returns:
            是否被撤销
        """
        return token_id in self._revoked_tokens

    def cleanup_expired_tokens(self, max_age: int = 86400) -> None:
        """
        清理过期的撤销记录

        Args:
            max_age: 最大保留时间（秒）
        """
        now = time.time()
        expired_tokens = [
            token_id
            for token_id, revoke_time in self._revoked_tokens.items()
            if now - revoke_time > max_age
        ]

        for token_id in expired_tokens:
            del self._revoked_tokens[token_id]


# ============================================================================
# 认证上下文
# ============================================================================

class AuthContext:
    """认证上下文"""

    def __init__(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None
    ):
        """
        初始化认证上下文

        Args:
            user_id: 用户 ID
            account_id: 账号 ID
            roles: 角色列表
            permissions: 权限列表
        """
        self.user_id = user_id
        self.account_id = account_id
        self.roles = roles or []
        self.permissions = permissions or []

    def has_role(self, role: str) -> bool:
        """
        检查是否有指定角色

        Args:
            role: 角色名

        Returns:
            是否有该角色
        """
        return role in self.roles

    def has_any_role(self, roles: List[str]) -> bool:
        """
        检查是否有任意一个角色

        Args:
            roles: 角色列表

        Returns:
            是否有任意一个角色
        """
        return any(role in self.roles for role in roles)

    def has_all_roles(self, roles: List[str]) -> bool:
        """
        检查是否有所有角色

        Args:
            roles: 角色列表

        Returns:
            是否有所有角色
        """
        return all(role in self.roles for role in roles)

    def has_permission(self, permission: str) -> bool:
        """
        检查是否有指定权限

        Args:
            permission: 权限名

        Returns:
            是否有该权限
        """
        return permission in self.permissions

    def has_any_permission(self, permissions: List[str]) -> bool:
        """
        检查是否有任意一个权限

        Args:
            permissions: 权限列表

        Returns:
            是否有任意一个权限
        """
        return any(perm in self.permissions for perm in permissions)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            字典表示
        """
        return {
            "user_id": self.user_id,
            "account_id": self.account_id,
            "roles": self.roles,
            "permissions": self.permissions
        }


# ============================================================================
# 便捷函数
# ============================================================================

def create_auth_context_from_token(token: str, jwt_manager: JWTManager) -> AuthContext:
    """
    从令牌创建认证上下文

    Args:
        token: JWT 访问令牌
        jwt_manager: JWT 管理器

    Returns:
        认证上下文

    Raises:
        AuthenticationError: 令牌无效
    """
    payload = jwt_manager.verify_access_token(token)

    return AuthContext(
        user_id=payload["sub"],
        account_id=payload.get("account_id"),
        roles=payload.get("roles", []),
        permissions=payload.get("permissions", [])
    )


def hash_password(password: str) -> str:
    """
    哈希密码

    Args:
        password: 明文密码

    Returns:
        哈希后的密码
    """
    import hashlib

    # 使用 SHA-256 哈希（生产环境应使用 bcrypt）
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """
    验证密码

    Args:
        password: 明文密码
        hashed: 哈希后的密码

    Returns:
        是否匹配
    """
    return hash_password(password) == hashed
