"""
小红书 AI 运营系统 - 安全模块

提供密钥管理、敏感数据保护和安全工具函数。
"""

import os
import json
import hashlib
import hmac
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from functools import wraps

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logging.warning("keyring not installed, using environment variables only")

logger = logging.getLogger(__name__)


class KeyManager:
    """
    密钥管理器 - 安全存储和访问 API 密钥

    支持多种存储方式（按优先级）:
    1. keyring (系统密钥环)
    2. 环境变量
    3. 加密的配置文件
    """

    # 允许的密钥名称
    ALLOWED_KEYS = [
        "STABILITY_API_KEY",
        "OPENAI_API_KEY",
        "REPLICATE_API_TOKEN",
        "HUGGINGFACE_API_KEY",
        "IDEOGRAM_API_KEY",
        "LEONARDO_API_KEY",
        "TAVILY_API_KEY"
    ]

    def __init__(self, service_name: str = "xhs-operator"):
        """
        初始化密钥管理器

        Args:
            service_name: 服务名称，用于 keyring 标识
        """
        self.service_name = service_name
        self._cache: Dict[str, str] = {}

    def get(self, key_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取 API 密钥

        按优先级从多个来源获取:
        1. 内存缓存
        2. keyring
        3. 环境变量

        Args:
            key_name: 密钥名称
            default: 默认值（如果未找到）

        Returns:
            密钥值或默认值
        """
        # 验证密钥名称
        if key_name not in self.ALLOWED_KEYS:
            logger.warning(f"Attempted to access non-allowed key: {key_name}")
            return default

        # 检查缓存
        if key_name in self._cache:
            return self._cache[key_name]

        # 尝试从 keyring 获取
        if KEYRING_AVAILABLE:
            try:
                value = keyring.get_password(self.service_name, key_name)
                if value:
                    self._cache[key_name] = value
                    logger.debug(f"Retrieved {key_name} from keyring")
                    return value
            except Exception as e:
                logger.warning(f"Failed to get {key_name} from keyring: {e}")

        # 尝试从环境变量获取
        value = os.getenv(key_name)
        if value:
            self._cache[key_name] = value
            logger.debug(f"Retrieved {key_name} from environment")
            return value

        logger.warning(f"Key not found: {key_name}")
        return default

    def set(self, key_name: str, value: str) -> bool:
        """
        设置 API 密钥

        Args:
            key_name: 密钥名称
            value: 密钥值

        Returns:
            是否成功
        """
        if key_name not in self.ALLOWED_KEYS:
            logger.error(f"Attempted to set non-allowed key: {key_name}")
            return False

        # 验证密钥值
        if not value or not value.strip():
            logger.error(f"Attempted to set empty key: {key_name}")
            return False

        # 存储到 keyring
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(self.service_name, key_name, value)
                logger.info(f"Stored {key_name} in keyring")
            except Exception as e:
                logger.error(f"Failed to store {key_name} in keyring: {e}")
                return False

        # 更新缓存
        self._cache[key_name] = value
        return True

    def validate(self, key_name: str) -> Dict[str, Any]:
        """
        验证密钥是否有效且格式正确

        Args:
            key_name: 密钥名称

        Returns:
            验证结果字典
        """
        value = self.get(key_name)

        result = {
            "key_name": key_name,
            "valid": False,
            "format": "unknown",
            "prefix": None,
            "issues": []
        }

        if not value:
            result["issues"].append("Key not found")
            return result

        # 检查密钥格式
        if key_name == "STABILITY_API_KEY":
            if value.startswith("sk-"):
                result["format"] = "Stability AI"
                result["prefix"] = "sk-"
                if len(value) >= 40:  # Stability AI keys are typically 48 chars
                    result["valid"] = True
                else:
                    result["issues"].append("Key length too short")
            else:
                result["issues"].append("Invalid prefix (should start with sk-)")

        elif key_name == "OPENAI_API_KEY":
            if value.startswith("sk-"):
                result["format"] = "OpenAI"
                result["prefix"] = "sk-"
                if len(value) >= 20:  # OpenAI keys are typically 51 chars
                    result["valid"] = True
                else:
                    result["issues"].append("Key length too short")
            else:
                result["issues"].append("Invalid prefix (should start with sk-)")

        elif key_name == "REPLICATE_API_TOKEN":
            if value.startswith("r8_"):
                result["format"] = "Replicate"
                result["prefix"] = "r8_"
                if len(value) >= 10:
                    result["valid"] = True
                else:
                    result["issues"].append("Key length too short")
            else:
                result["issues"].append("Invalid prefix (should start with r8_)")

        elif key_name == "HUGGINGFACE_API_KEY":
            if value.startswith("hf_"):
                result["format"] = "Hugging Face"
                result["prefix"] = "hf_"
                if len(value) >= 10:
                    result["valid"] = True
                else:
                    result["issues"].append("Key length too short")
            else:
                result["issues"].append("Invalid prefix (should start with hf_)")

        else:
            # 其他密钥的基本验证
            if len(value) >= 10:
                result["valid"] = True
            else:
                result["issues"].append("Key length too short")

        return result

    def remove(self, key_name: str) -> bool:
        """
        删除密钥

        Args:
            key_name: 密钥名称

        Returns:
            是否成功
        """
        if key_name in self._cache:
            del self._cache[key_name]

        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(self.service_name, key_name)
                logger.info(f"Removed {key_name} from keyring")
                return True
            except Exception as e:
                logger.error(f"Failed to remove {key_name} from keyring: {e}")
                return False

        return True


class SecureConfig:
    """
    安全配置管理器

    处理敏感配置文件的加密和解密
    """

    def __init__(self, config_path: Path):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self._encryption_key: Optional[bytes] = None

    def _get_encryption_key(self) -> bytes:
        """
        获取或生成加密密钥

        Returns:
            加密密钥
        """
        if self._encryption_key is None:
            # 从环境变量获取
            key_str = os.getenv("XHS_ENCRYPTION_KEY")
            if key_str:
                self._encryption_key = key_str.encode()
            else:
                # 基于机器特征生成密钥
                machine_id = os.uname().nodename + os.uname().machine
                self._encryption_key = hashlib.sha256(
                    machine_id.encode()
                ).digest()
                logger.warning("Using machine-specific encryption key")

        return self._encryption_key

    def encrypt_value(self, value: str) -> str:
        """
        加密字符串值

        Args:
            value: 明文字符串

        Returns:
            加密后的字符串（base64编码）
        """
        try:
            from cryptography.fernet import Fernet
            key = self._get_encryption_key()
            f = Fernet(key)
            encrypted = f.encrypt(value.encode())
            return encrypted.decode()
        except ImportError:
            logger.warning("cryptography not installed, using base64 encoding")
            import base64
            return base64.b64encode(value.encode()).decode()

    def decrypt_value(self, encrypted_value: str) -> str:
        """
        解密字符串值

        Args:
            encrypted_value: 加密的字符串

        Returns:
            明文字符串
        """
        try:
            from cryptography.fernet import Fernet
            key = self._get_encryption_key()
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except ImportError:
            logger.warning("cryptography not installed, using base64 decoding")
            import base64
            return base64.b64decode(encrypted_value.encode()).decode()

    def encrypt_sensitive_fields(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        加密配置中的敏感字段

        Args:
            config: 配置字典

        Returns:
            加密后的配置字典
        """
        sensitive_keys = [
            "api_key", "token", "password", "secret",
            "cookie", "cookies", "auth_token"
        ]

        encrypted_config = config.copy()

        for key, value in config.items():
            # 检查是否是敏感字段
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and value:
                    encrypted_config[key] = self.encrypt_value(value)
            # 处理嵌套字典
            elif isinstance(value, dict):
                encrypted_config[key] = self.encrypt_sensitive_fields(value)

        return encrypted_config

    def decrypt_sensitive_fields(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        解密配置中的敏感字段

        Args:
            config: 加密的配置字典

        Returns:
            解密后的配置字典
        """
        sensitive_keys = [
            "api_key", "token", "password", "secret",
            "cookie", "cookies", "auth_token"
        ]

        decrypted_config = config.copy()

        for key, value in config.items():
            # 检查是否是敏感字段
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and value:
                    try:
                        decrypted_config[key] = self.decrypt_value(value)
                    except Exception as e:
                        logger.warning(f"Failed to decrypt {key}: {e}")
            # 处理嵌套字典
            elif isinstance(value, dict):
                decrypted_config[key] = self.decrypt_sensitive_fields(value)

        return decrypted_config


class SensitiveDataFilter(logging.Filter):
    """
    敏感数据过滤器 - 过滤日志中的敏感信息
    """

    # 敏感信息正则模式
    SENSITIVE_PATTERNS = [
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?[\w-]+', '[API_KEY_REDACTED]'),
        (r'token["\']?\s*[:=]\s*["\']?[\w-]+', '[TOKEN_REDACTED]'),
        (r'password["\']?\s*[:=]\s*["\'][^"\']+["\']', '[PASSWORD_REDACTED]'),
        (r'secret["\']?\s*[:=]\s*["\'][^"\']+["\']', '[SECRET_REDACTED]'),
        (r'cookie["\']?\s*[:=]\s*["\'][^"\']+["\']', '[COOKIE_REDACTED]'),
        (r'Authorization:\s*Bearer\s+[\w-\.]+', '[AUTH_REDACTED]'),
    ]

    def __init__(self):
        super().__init__()
        import re
        self.patterns = [(re.compile(p, re.IGNORECASE), r) for p, r in self.SENSITIVE_PATTERNS]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        过滤日志记录中的敏感信息

        Args:
            record: 日志记录

        Returns:
            True (总是记录日志)
        """
        if isinstance(record.msg, str):
            for pattern, replacement in self.patterns:
                record.msg = pattern.sub(replacement, record.msg)

        return True


def setup_secure_logging(service_name: str, log_file: Optional[Path] = None) -> logging.Logger:
    """
    配置安全的日志系统

    Args:
        service_name: 服务名称
        log_file: 日志文件路径（可选）

    Returns:
        配置好的 logger
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)

    # 添加敏感数据过滤器
    logger.addFilter(SensitiveDataFilter())

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 简洁的格式（避免敏感信息）
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（如果指定）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def validate_config_permissions(config_path: Path) -> Dict[str, Any]:
    """
    验证配置文件权限

    Args:
        config_path: 配置文件路径

    Returns:
        验证结果字典
    """
    result = {
        "path": str(config_path),
        "exists": config_path.exists(),
        "secure": False,
        "issues": [],
        "permissions": None
    }

    if not config_path.exists():
        result["issues"].append("File does not exist")
        return result

    # 获取文件权限
    stat_info = config_path.stat()
    mode = oct(stat_info.st_mode)[-3:]
    result["permissions"] = mode

    # 检查权限是否过于宽松
    if mode in ["644", "666", "777"]:
        result["issues"].append(f"Permissions too loose: {mode}")
        result["issues"].append("Should be 600 (owner read/write only)")

    # 检查是否包含敏感信息
    if config_path.suffix in [".json", ".yaml", ".yml"]:
        try:
            content = config_path.read_text()

            # 检查是否包含可能敏感的键名
            sensitive_keywords = ["api_key", "token", "password", "secret", "cookie"]
            for keyword in sensitive_keywords:
                if keyword in content.lower():
                    result["issues"].append(f"Contains sensitive keyword: {keyword}")
        except Exception as e:
            result["issues"].append(f"Could not read file: {e}")

    # 如果没有问题，认为是安全的
    if len(result["issues"]) == 0:
        result["secure"] = True

    return result


def generate_request_id() -> str:
    """
    生成唯一的请求ID

    Returns:
        请求ID
    """
    import uuid
    return f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


# 便捷函数
key_manager = KeyManager()

def get_api_key(key_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    获取 API 密钥的便捷函数

    Args:
        key_name: 密钥名称
        default: 默认值

    Returns:
        密钥值
    """
    return key_manager.get(key_name, default)


def validate_api_key(key_name: str) -> Dict[str, Any]:
    """
    验证 API 密钥的便捷函数

    Args:
        key_name: 密钥名称

    Returns:
        验证结果
    """
    return key_manager.validate(key_name)
