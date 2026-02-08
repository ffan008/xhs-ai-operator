#!/usr/bin/env python3
"""
交互式配置向导

引导用户完成系统配置，自动生成配置文件。
"""

import os
import sys
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from common.validators import validate_email, validate_url
    from common.security import generate_jwt_secret, generate_api_key
except ImportError:
    # 如果导入失败，提供简单的实现
    def validate_email(email: str) -> bool:
        return "@" in email and "." in email

    def validate_url(url: str) -> bool:
        return url.startswith(("http://", "https://"))

    def generate_jwt_secret() -> str:
        import secrets
        return secrets.token_hex(32)

    def generate_api_key() -> str:
        import secrets
        return f"sk_{secrets.token_hex(32)}"


# ============================================================================
# 颜色输出
# ============================================================================

class Colors:
    """终端颜色"""
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text: str) -> None:
    """打印标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text: str) -> None:
    """打印成功消息"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    """打印错误消息"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text: str) -> None:
    """打印警告消息"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    """打印信息"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_step(step: int, total: int, title: str) -> None:
    """打印步骤"""
    print(f"\n{Colors.OKBLUE}[步骤 {step}/{total}] {Colors.BOLD}{title}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'─'*60}{Colors.ENDC}")


# ============================================================================
# 输入验证
# ============================================================================

def validate_required(value: str) -> bool:
    """验证必填项"""
    return bool(value.strip())


def validate_port(value: str) -> bool:
    """验证端口号"""
    try:
        port = int(value)
        return 1 <= port <= 65535
    except ValueError:
        return False


def validate_choice(value: str, choices: List[str]) -> bool:
    """验证选择"""
    return value.lower() in [c.lower() for c in choices]


# ============================================================================
# 配置向导
# ============================================================================

class ConfigWizard:
    """配置向导"""

    def __init__(self):
        """初始化配置向导"""
        self.config = {}
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 支持的图像生成服务
        self.image_services = {
            "1": ("stability", "Stability AI", "https://api.stability.ai"),
            "2": ("openai", "OpenAI DALL-E", "https://api.openai.com"),
            "3": ("midjourney", "Midjourney", "https://api.mjourney.com"),
            "4": ("replicate", "Replicate", "https://api.replicate.com"),
            "5": ("huggingface", "Hugging Face", "https://api-inference.huggingface.co"),
            "6": ("local", "本地 Stable Diffusion", "http://127.0.0.1:7860")
        }

    def input_str(
        self,
        prompt: str,
        default: str = "",
        required: bool = True,
        validator: Optional[callable] = None,
        help_text: str = ""
    ) -> str:
        """
        输入字符串

        Args:
            prompt: 提示文本
            default: 默认值
            required: 是否必填
            validator: 验证函数
            help_text: 帮助文本

        Returns:
            用户输入的值
        """
        if help_text:
            print(f"{Colors.OKCYAN}💡 {help_text}{Colors.ENDC}")

        default_prompt = f" [{default}]" if default else ""
        while True:
            value = input(f"{Colors.BOLD}{prompt}{default_prompt}: {Colors.ENDC}").strip()

            # 使用默认值
            if not value and default:
                return default

            # 必填验证
            if required and not value:
                print_error("此项为必填，请输入")
                continue

            # 自定义验证
            if validator and value:
                if validator(value):
                    return value
                else:
                    print_error("输入格式不正确，请重新输入")
                    continue

            return value

    def input_choice(
        self,
        prompt: str,
        choices: List[str],
        default: int = 0
    ) -> str:
        """
        输入选择

        Args:
            prompt: 提示文本
            choices: 选项列表
            default: 默认选项索引

        Returns:
            选择的值
        """
        for i, choice in enumerate(choices, 1):
            marker = "▶" if i - 1 == default else " "
            print(f"  {marker} {i}. {choice}")

        while True:
            value = input(f"\n{Colors.BOLD}请选择 [1-{len(choices)}]: {Colors.ENDC}").strip()

            if not value and default >= 0:
                return choices[default]

            try:
                index = int(value) - 1
                if 0 <= index < len(choices):
                    return choices[index]
            except ValueError:
                pass

            print_error(f"请输入 1-{len(choices)} 之间的数字")

    def input_yes_no(self, prompt: str, default: bool = True) -> bool:
        """
        输入是/否

        Args:
            prompt: 提示文本
            default: 默认值

        Returns:
            True 或 False
        """
        choices = ["是", "否"]
        default_index = 0 if default else 1

        choice = self.input_choice(prompt, choices, default_index)
        return choice == "是"

    def run(self) -> None:
        """运行配置向导"""
        print_header("小红书 AI 运营系统 - 配置向导")
        print_info("本向导将引导您完成系统配置")
        print_info("预计时间: 3-5 分钟\n")

        total_steps = 7

        # 步骤 1: 基本配置
        print_step(1, total_steps, "基本配置")
        self._step_basic_config()

        # 步骤 2: 小红书账号
        print_step(2, total_steps, "小红书账号配置")
        self._step_xiaohongshu_account()

        # 步骤 3: 图像生成服务
        print_step(3, total_steps, "图像生成服务配置")
        self._step_image_service()

        # 步骤 4: 数据存储配置
        print_step(4, total_steps, "数据存储配置")
        self._step_storage_config()

        # 步骤 5: Redis 配置
        print_step(5, total_steps, "Redis 配置")
        self._step_redis_config()

        # 步骤 6: 调度器配置
        print_step(6, total_steps, "调度器配置")
        self._step_scheduler_config()

        # 步骤 7: 生成配置文件
        print_step(7, total_steps, "生成配置文件")
        self._step_generate_files()

        # 完成
        print_header("配置完成")
        self._print_summary()

    def _step_basic_config(self) -> None:
        """基本配置"""
        print_info("请输入基本配置信息\n")

        # 项目名称
        self.config["project_name"] = self.input_str(
            "项目名称",
            default="小红书 AI 运营系统",
            required=True
        )

        # 环境
        env = self.input_choice(
            "运行环境",
            ["开发环境 (development)", "生产环境 (production)"],
            default=0
        )
        self.config["environment"] = "development" if "开发" in env else "production"

        # 日志级别
        log_level = self.input_choice(
            "日志级别",
            ["DEBUG", "INFO", "WARNING", "ERROR"],
            default=1
        )
        self.config["log_level"] = log_level

        # API 端口
        self.config["api_port"] = self.input_str(
            "API 服务端口",
            default="8080",
            validator=validate_port
        )

        # 时区
        self.config["timezone"] = self.input_str(
            "时区",
            default="Asia/Shanghai"
        )

        print_success("基本配置完成")

    def _step_xiaohongshu_account(self) -> None:
        """小红书账号配置"""
        print_info("配置小红书账号信息\n")

        has_account = self.input_yes_no("是否已有小红书账号？", default=True)

        if has_account:
            # 账号 ID
            self.config["xhs_account_id"] = self.input_str(
                "账号 ID（可选）",
                default="",
                required=False
            ) or f"account_{uuid.uuid4().hex[:8]}"

            # Cookies
            print_warning("请从小红书网页版获取 Cookies")
            print_info("1. 打开浏览器访问 https://www.xiaohongshu.com")
            print_info("2. 登录后按 F12 打开开发者工具")
            print_info("3. 在 Application > Cookies 中复制所有 Cookie\n")

            self.config["xhs_cookies"] = self.input_str(
                "请粘贴 Cookies（可选，稍后也可配置）",
                default="",
                required=False
            )

            # 账号名称
            self.config["xhs_account_name"] = self.input_str(
                "账号名称（便于识别）",
                default="我的小红书账号",
                required=True
            )
        else:
            print_warning("您可以在稍后配置账号信息")
            self.config["xhs_account_id"] = f"account_{uuid.uuid4().hex[:8]}"
            self.config["xhs_cookies"] = ""
            self.config["xhs_account_name"] = "未配置"

        print_success("小红书账号配置完成")

    def _step_image_service(self) -> None:
        """图像生成服务配置"""
        print_info("选择图像生成服务\n")

        print("支持的图像生成服务:")
        for key, (service_id, name, url) in self.image_services.items():
            print(f"  {key}. {name} ({url})")

        choice = self.input_choice(
            "\n选择图像生成服务",
            list(self.image_services.keys()),
            default=0
        )

        service_id, service_name, service_url = self.image_services[choice]
        self.config["image_service"] = service_id
        self.config["image_service_name"] = service_name
        self.config["image_service_url"] = service_url

        # API Key
        if service_id != "local":
            print_info(f"\n配置 {service_name} API Key")
            print_warning(f"请访问 {service_name} 官网获取 API Key")

            self.config["image_api_key"] = self.input_str(
                f"{service_name} API Key（可选，稍后也可配置）",
                default="",
                required=False
            )
        else:
            print_info("\n本地 Stable Diffusion 配置")
            self.config["image_api_key"] = ""

            # 本地服务地址
            local_url = self.input_str(
                "本地服务地址",
                default="http://127.0.0.1:7860",
                validator=validate_url
            )
            self.config["image_service_url"] = local_url

        print_success(f"图像生成服务配置完成: {service_name}")

    def _step_storage_config(self) -> None:
        """数据存储配置"""
        print_info("配置数据存储\n")

        # 数据存储路径
        default_storage = str(self.project_root / "data")
        self.config["storage_path"] = self.input_str(
            "数据存储路径",
            default=default_storage,
            required=True
        )

        # 数据库类型
        db_type = self.input_choice(
            "数据库类型",
            ["SQLite（推荐，无需额外配置）", "MySQL", "PostgreSQL"],
            default=0
        )

        if "SQLite" in db_type:
            self.config["database_type"] = "sqlite"
            self.config["database_path"] = str(Path(self.config["storage_path"]) / "database.db")
        elif "MySQL" in db_type:
            self.config["database_type"] = "mysql"
            self.config["mysql_host"] = self.input_str("MySQL 主机", default="localhost")
            self.config["mysql_port"] = self.input_str("MySQL 端口", default="3306", validator=validate_port)
            self.config["mysql_database"] = self.input_str("数据库名", default="xiaohongshu_ai", required=True)
            self.config["mysql_username"] = self.input_str("用户名", default="root", required=True)
            self.config["mysql_password"] = self.input_str("密码", default="", required=False)
        else:  # PostgreSQL
            self.config["database_type"] = "postgresql"
            self.config["postgres_host"] = self.input_str("PostgreSQL 主机", default="localhost")
            self.config["postgres_port"] = self.input_str("PostgreSQL 端口", default="5432", validator=validate_port)
            self.config["postgres_database"] = self.input_str("数据库名", default="xiaohongshu_ai", required=True)
            self.config["postgres_username"] = self.input_str("用户名", default="postgres", required=True)
            self.config["postgres_password"] = self.input_str("密码", default="", required=False)

        print_success("数据存储配置完成")

    def _step_redis_config(self) -> None:
        """Redis 配置"""
        print_info("配置 Redis（用于缓存和分布式调度）\n")

        use_redis = self.input_yes_no("是否使用 Redis？（推荐使用）", default=True)

        if use_redis:
            self.config["redis_enabled"] = True
            self.config["redis_host"] = self.input_str("Redis 主机", default="localhost")
            self.config["redis_port"] = self.input_str("Redis 端口", default="6379", validator=validate_port)

            use_password = self.input_yes_no("Redis 是否需要密码？", default=False)
            if use_password:
                self.config["redis_password"] = self.input_str("Redis 密码", required=True)
            else:
                self.config["redis_password"] = ""

            self.config["redis_db"] = self.input_str("Redis 数据库编号", default="0", required=False)

            print_success("Redis 配置完成")
        else:
            print_warning("不使用 Redis，将使用内存缓存（功能受限）")
            self.config["redis_enabled"] = False

    def _step_scheduler_config(self) -> None:
        """调度器配置"""
        print_info("配置定时任务调度器\n")

        enable_scheduler = self.input_yes_no("是否启用定时任务调度？", default=True)
        self.config["scheduler_enabled"] = enable_scheduler

        if enable_scheduler:
            # 调度间隔
            self.config["scheduler_tick_interval"] = self.input_str(
                "调度检查间隔（秒）",
                default="60",
                validator=lambda x: x.isdigit() and int(x) > 0
            )

            # 并发数
            self.config["scheduler_max_concurrent"] = self.input_str(
                "最大并发任务数",
                default="5",
                validator=lambda x: x.isdigit() and int(x) > 0
            )

            print_success("调度器配置完成")
        else:
            self.config["scheduler_tick_interval"] = "60"
            self.config["scheduler_max_concurrent"] = "5"

    def _step_generate_files(self) -> None:
        """生成配置文件"""
        print_info("正在生成配置文件...\n")

        # 创建必要的目录
        directories = [
            Path(self.config["storage_path"]),
            self.config_dir / "accounts",
            Path(self.config["storage_path"]) / "logs",
            Path(self.config["storage_path"]) / "cache",
            Path(self.config["storage_path"]) / "uploads"
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print_success(f"创建目录: {directory}")

        # 生成 .env 文件
        env_file = self.project_root / ".env"
        self._generate_env_file(env_file)

        # 生成账号配置
        self._generate_account_config()

        # 生成图像服务配置
        self._generate_image_config()

        print_success("配置文件生成完成")

    def _generate_env_file(self, env_file: Path) -> None:
        """生成 .env 文件"""
        env_content = f"""# 小红书 AI 运营系统 - 环境配置
# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# 基本配置
PROJECT_NAME={self.config.get("project_name", "小红书 AI 运营系统")}
ENVIRONMENT={self.config.get("environment", "development")}
LOG_LEVEL={self.config.get("log_level", "INFO")}
TIMEZONE={self.config.get("timezone", "Asia/Shanghai")}

# API 配置
API_PORT={self.config.get("api_port", "8080")}
API_HOST=0.0.0.0

# 安全配置
JWT_SECRET={generate_jwt_secret()}
API_KEY={generate_api_key()}

# 数据存储
STORAGE_PATH={self.config.get("storage_path", "./data")}
DATABASE_TYPE={self.config.get("database_type", "sqlite")}
"""

        # 数据库配置
        if self.config.get("database_type") == "sqlite":
            env_content += f"DATABASE_PATH={self.config.get('database_path', './data/database.db')}\n"
        elif self.config.get("database_type") == "mysql":
            env_content += f"""MYSQL_HOST={self.config.get('mysql_host', 'localhost')}
MYSQL_PORT={self.config.get('mysql_port', '3306')}
MYSQL_DATABASE={self.config.get('mysql_database', 'xiaohongshu_ai')}
MYSQL_USERNAME={self.config.get('mysql_username', 'root')}
MYSQL_PASSWORD={self.config.get('mysql_password', '')}
"""
        elif self.config.get("database_type") == "postgresql":
            env_content += f"""POSTGRES_HOST={self.config.get('postgres_host', 'localhost')}
POSTGRES_PORT={self.config.get('postgres_port', '5432')}
POSTGRES_DATABASE={self.config.get('postgres_database', 'xiaohongshu_ai')}
POSTGRES_USERNAME={self.config.get('postgres_username', 'postgres')}
POSTGRES_PASSWORD={self.config.get('postgres_password', '')}
"""

        # Redis 配置
        if self.config.get("redis_enabled"):
            env_content += f"""# Redis 配置
REDIS_ENABLED=true
REDIS_HOST={self.config.get('redis_host', 'localhost')}
REDIS_PORT={self.config.get('redis_port', '6379')}
REDIS_PASSWORD={self.config.get('redis_password', '')}
REDIS_DB={self.config.get('redis_db', '0')}
"""
        else:
            env_content += "\n# Redis 配置（未启用）\nREDIS_ENABLED=false\n"

        # 调度器配置
        if self.config.get("scheduler_enabled"):
            env_content += f"""# 调度器配置
SCHEDULER_ENABLED=true
SCHEDULER_TICK_INTERVAL={self.config.get('scheduler_tick_interval', '60')}
SCHEDULER_MAX_CONCURRENT={self.config.get('scheduler_max_concurrent', '5')}
"""
        else:
            env_content += "\n# 调度器配置（未启用）\nSCHEDULER_ENABLED=false\n"

        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)

        # 设置权限
        env_file.chmod(0o600)

        print_success(f"生成文件: {env_file}")

    def _generate_account_config(self) -> None:
        """生成账号配置"""
        # 确保账号目录存在
        accounts_dir = self.config_dir / "accounts"
        accounts_dir.mkdir(parents=True, exist_ok=True)

        account_file = accounts_dir / f"{self.config.get('xhs_account_id')}.json"

        account_data = {
            "account_id": self.config.get("xhs_account_id"),
            "account_name": self.config.get("xhs_account_name"),
            "platform": "xiaohongshu",
            "enabled": True,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "image_service": self.config.get("image_service")
            }
        }

        # 保存 Cookies（如果有）
        if self.config.get("xhs_cookies"):
            account_data["cookies"] = {"raw": self.config.get("xhs_cookies")}

        with open(account_file, "w", encoding="utf-8") as f:
            json.dump(account_data, f, indent=2, ensure_ascii=False)

        account_file.chmod(0o600)

        print_success(f"生成文件: {account_file}")

    def _generate_image_config(self) -> None:
        """生成图像服务配置"""
        image_config_file = self.config_dir / "image_services.json"

        image_config = {
            "default_service": self.config.get("image_service"),
            "services": {
                self.config.get("image_service"): {
                    "name": self.config.get("image_service_name"),
                    "base_url": self.config.get("image_service_url"),
                    "api_key": self.config.get("image_api_key", ""),
                    "enabled": True
                }
            }
        }

        with open(image_config_file, "w", encoding="utf-8") as f:
            json.dump(image_config, f, indent=2, ensure_ascii=False)

        print_success(f"生成文件: {image_config_file}")

    def _print_summary(self) -> None:
        """打印配置摘要"""
        print_info("配置摘要:\n")

        print(f"  项目名称: {self.config.get('project_name')}")
        print(f"  运行环境: {self.config.get('environment')}")
        print(f"  数据库: {self.config.get('database_type')}")
        print(f"  Redis: {'启用' if self.config.get('redis_enabled') else '未启用'}")
        print(f"  图像服务: {self.config.get('image_service_name')}")
        print(f"  调度器: {'启用' if self.config.get('scheduler_enabled') else '未启用'}")

        print()
        print_success("配置已完成！")
        print_info("\n后续步骤:")
        print("  1. 检查生成的 .env 文件")
        print("  2. 安装依赖: pip install -r requirements.txt")
        print("  3. 配置小红书账号 Cookies（如果未配置）")
        print("  4. 启动系统: python main.py")
        print()
        print_info("如需修改配置，请重新运行此向导或直接编辑 .env 文件")
        print()


# ============================================================================
# 主程序
# ============================================================================

def main():
    """主程序"""
    try:
        wizard = ConfigWizard()
        wizard.run()
    except KeyboardInterrupt:
        print_warning("\n\n配置已取消")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n配置失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
