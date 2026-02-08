"""
账号隔离模块

实现多账号数据隔离，确保不同账号的数据严格分离。
"""

import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from threading import Lock
from .exceptions import BusinessError, ConfigurationError, SecurityError


# ============================================================================
# 账号配置
# ============================================================================

class AccountConfig:
    """账号配置"""

    def __init__(
        self,
        account_id: str,
        account_name: str,
        platform: str = "xiaohongshu",
        cookies: Optional[Dict[str, str]] = None,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化账号配置

        Args:
            account_id: 账号 ID
            account_name: 账号名称
            platform: 平台
            cookies: 登录 cookies
            enabled: 是否启用
            metadata: 元数据
        """
        self.account_id = account_id
        self.account_name = account_name
        self.platform = platform
        self.cookies = cookies or {}
        self.enabled = enabled
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（不包含敏感信息）

        Returns:
            字典表示
        """
        return {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "platform": self.platform,
            "enabled": self.enabled,
            "metadata": self.metadata
        }


# ============================================================================
# 账号管理器
# ============================================================================

class AccountManager:
    """账号管理器"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化账号管理器

        Args:
            config_dir: 配置目录（如果为 None，使用默认目录）
        """
        self.config_dir = config_dir or Path("config/accounts")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()

        # 账号配置缓存
        self._accounts: Dict[str, AccountConfig] = {}

        # 加载所有账号
        self._load_accounts()

    def _get_account_file(self, account_id: str) -> Path:
        """
        获取账号配置文件路径

        Args:
            account_id: 账号 ID

        Returns:
            配置文件路径
        """
        return self.config_dir / f"{account_id}.json"

    def _load_accounts(self) -> None:
        """加载所有账号配置"""
        with self.lock:
            self._accounts.clear()

            for account_file in self.config_dir.glob("*.json"):
                try:
                    with open(account_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    account = AccountConfig(
                        account_id=data["account_id"],
                        account_name=data["account_name"],
                        platform=data.get("platform", "xiaohongshu"),
                        cookies=data.get("cookies", {}),
                        enabled=data.get("enabled", True),
                        metadata=data.get("metadata", {})
                    )

                    self._accounts[account.account_id] = account

                except Exception as e:
                    # 记录错误但继续加载其他账号
                    print(f"Failed to load account from {account_file}: {e}")

    def _save_account(self, account: AccountConfig) -> None:
        """
        保存账号配置

        Args:
            account: 账号配置
        """
        account_file = self._get_account_file(account.account_id)

        data = {
            "account_id": account.account_id,
            "account_name": account.account_name,
            "platform": account.platform,
            "cookies": account.cookies,
            "enabled": account.enabled,
            "metadata": account.metadata
        }

        with open(account_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 设置文件权限
        account_file.chmod(0o600)

    def add_account(self, account: AccountConfig) -> None:
        """
        添加账号

        Args:
            account: 账号配置

        Raises:
            BusinessError: 账号已存在
        """
        with self.lock:
            if account.account_id in self._accounts:
                raise BusinessError(
                    message=f"Account already exists: {account.account_id}",
                    user_message=f"账号已存在: {account.account_id}"
                )

            self._accounts[account.account_id] = account
            self._save_account(account)

    def update_account(self, account_id: str, updates: Dict[str, Any]) -> None:
        """
        更新账号

        Args:
            account_id: 账号 ID
            updates: 更新内容

        Raises:
            BusinessError: 账号不存在
        """
        with self.lock:
            if account_id not in self._accounts:
                raise BusinessError(
                    message=f"Account not found: {account_id}",
                    user_message=f"账号不存在: {account_id}"
                )

            account = self._accounts[account_id]

            # 更新字段
            if "account_name" in updates:
                account.account_name = updates["account_name"]
            if "cookies" in updates:
                account.cookies = updates["cookies"]
            if "enabled" in updates:
                account.enabled = updates["enabled"]
            if "metadata" in updates:
                account.metadata.update(updates["metadata"])

            self._save_account(account)

    def delete_account(self, account_id: str) -> None:
        """
        删除账号

        Args:
            account_id: 账号 ID

        Raises:
            BusinessError: 账号不存在
        """
        with self.lock:
            if account_id not in self._accounts:
                raise BusinessError(
                    message=f"Account not found: {account_id}",
                    user_message=f"账号不存在: {account_id}"
                )

            # 删除配置文件
            account_file = self._get_account_file(account_id)
            account_file.unlink()

            # 从缓存中移除
            del self._accounts[account_id]

    def get_account(self, account_id: str) -> Optional[AccountConfig]:
        """
        获取账号

        Args:
            account_id: 账号 ID

        Returns:
            账号配置（如果存在）
        """
        return self._accounts.get(account_id)

    def list_accounts(self, include_disabled: bool = False) -> List[AccountConfig]:
        """
        列出所有账号

        Args:
            include_disabled: 是否包含已禁用的账号

        Returns:
            账号列表
        """
        accounts = list(self._accounts.values())

        if not include_disabled:
            accounts = [acc for acc in accounts if acc.enabled]

        return accounts

    def enable_account(self, account_id: str) -> None:
        """
        启用账号

        Args:
            account_id: 账号 ID

        Raises:
            BusinessError: 账号不存在
        """
        self.update_account(account_id, {"enabled": True})

    def disable_account(self, account_id: str) -> None:
        """
        禁用账号

        Args:
            account_id: 账号 ID

        Raises:
            BusinessError: 账号不存在
        """
        self.update_account(account_id, {"enabled": False})


# ============================================================================
# 数据隔离器
# ============================================================================

class DataIsolator:
    """数据隔离器"""

    def __init__(self, account_manager: Optional[AccountManager] = None):
        """
        初始化数据隔离器

        Args:
            account_manager: 账号管理器（如果为 None，使用默认管理器）
        """
        self.account_manager = account_manager or AccountManager()

    def isolate_data_path(
        self,
        base_path: Path,
        account_id: str
    ) -> Path:
        """
        获取账号隔离的数据路径

        Args:
            base_path: 基础路径
            account_id: 账号 ID

        Returns:
            隔离后的路径

        Raises:
            SecurityError: 账号不存在或被禁用
        """
        # 验证账号
        account = self.account_manager.get_account(account_id)
        if not account:
            raise SecurityError(
                message=f"Account not found: {account_id}",
                user_message=f"账号不存在: {account_id}"
            )

        if not account.enabled:
            raise SecurityError(
                message=f"Account is disabled: {account_id}",
                user_message=f"账号已禁用: {account_id}"
            )

        # 构建隔离路径
        isolated_path = base_path / account_id

        # 确保路径存在
        isolated_path.mkdir(parents=True, exist_ok=True)

        return isolated_path

    def validate_account_access(
        self,
        account_id: str,
        auth_context_account_id: Optional[str] = None,
        is_admin: bool = False
    ) -> None:
        """
        验证账号访问权限

        Args:
            account_id: 要访问的账号 ID
            auth_context_account_id: 认证上下文中的账号 ID
            is_admin: 是否是管理员

        Raises:
            SecurityError: 权限不足
        """
        # 管理员可以访问所有账号
        if is_admin:
            return

        # 验证账号匹配
        if auth_context_account_id != account_id:
            raise SecurityError(
                message=f"Account access denied: {auth_context_account_id} -> {account_id}",
                user_message="没有权限访问该账号"
            )

        # 验证账号存在且启用
        account = self.account_manager.get_account(account_id)
        if not account:
            raise SecurityError(
                message=f"Account not found: {account_id}",
                user_message=f"账号不存在: {account_id}"
            )

        if not account.enabled:
            raise SecurityError(
                message=f"Account is disabled: {account_id}",
                user_message=f"账号已禁用: {account_id}"
            )


# ============================================================================
# 全局实例
# ============================================================================

# 默认账号管理器
default_account_manager = AccountManager()

# 默认数据隔离器
default_isolator = DataIsolator(default_account_manager)


# ============================================================================
# 便捷函数
# ============================================================================

def get_isolated_path(base_path: Path, account_id: str) -> Path:
    """
    获取账号隔离的路径

    Args:
        base_path: 基础路径
        account_id: 账号 ID

    Returns:
        隔离后的路径
    """
    return default_isolator.isolate_data_path(base_path, account_id)


def validate_account_access(
    account_id: str,
    auth_context_account_id: Optional[str] = None,
    is_admin: bool = False
) -> None:
    """
    验证账号访问权限

    Args:
        account_id: 要访问的账号 ID
        auth_context_account_id: 认证上下文中的账号 ID
        is_admin: 是否是管理员

    Raises:
        SecurityError: 权限不足
    """
    default_isolator.validate_account_access(
        account_id,
        auth_context_account_id,
        is_admin
    )
