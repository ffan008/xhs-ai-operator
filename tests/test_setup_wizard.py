"""
配置向导单元测试
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.setup_wizard import (
    Colors,
    validate_required,
    validate_port,
    validate_choice,
    ConfigWizard
)


# ============================================================================
# 验证函数测试
# ============================================================================

class TestValidators:
    """测试验证函数"""

    def test_validate_required(self):
        """测试必填验证"""
        assert validate_required("test") is True
        assert validate_required("  test  ") is True
        assert validate_required("") is False
        assert validate_required("   ") is False
        print("✅ 必填验证正确")

    def test_validate_port(self):
        """测试端口验证"""
        assert validate_port("80") is True
        assert validate_port("8080") is True
        assert validate_port("65535") is True
        assert validate_port("0") is False
        assert validate_port("65536") is False
        assert validate_port("abc") is False
        assert validate_port("-1") is False
        print("✅ 端口验证正确")

    def test_validate_choice(self):
        """测试选择验证"""
        choices = ["选项1", "选项2", "选项3"]
        assert validate_choice("选项1", choices) is True
        assert validate_choice("选项2", choices) is True
        assert validate_choice("选项4", choices) is False
        # 不区分大小写
        assert validate_choice("选项1", choices) is True
        print("✅ 选择验证正确")


# ============================================================================
# ConfigWizard 测试
# ============================================================================

class TestConfigWizard:
    """测试配置向导"""

    def test_initialization(self):
        """测试初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = ConfigWizard()
            wizard.config_dir = Path(tmpdir)

            assert wizard.config == {}
            assert len(wizard.image_services) == 6
            print("✅ 向导初始化正确")

    def test_image_services(self):
        """测试图像服务配置"""
        wizard = ConfigWizard()

        # 检查所有服务
        assert "1" in wizard.image_services
        assert "2" in wizard.image_services
        assert "3" in wizard.image_services
        assert "4" in wizard.image_services
        assert "5" in wizard.image_services
        assert "6" in wizard.image_services

        # 检查服务格式
        service_id, name, url = wizard.image_services["1"]
        assert service_id == "stability"
        assert "Stability" in name
        assert url.startswith("http")

        print("✅ 图像服务配置正确")

    @patch('builtins.input', return_value="测试项目")
    def test_input_str_with_default(self, mock_input):
        """测试字符串输入（使用默认值）"""
        wizard = ConfigWizard()

        # 空输入应该返回默认值
        with patch('builtins.input', return_value=""):
            result = wizard.input_str("提示", default="默认值")
            assert result == "默认值"

        print("✅ 字符串输入（默认值）正确")

    @patch('builtins.input', return_value="用户输入")
    def test_input_str_with_value(self, mock_input):
        """测试字符串输入（用户输入）"""
        wizard = ConfigWizard()

        result = wizard.input_str("提示", default="默认值")
        assert result == "用户输入"

        print("✅ 字符串输入（用户输入）正确")

    def test_input_str_validation(self):
        """测试字符串输入验证"""
        wizard = ConfigWizard()

        # 测试端口验证
        with patch('builtins.input', side_effect=["invalid", "8080"]):
            result = wizard.input_str("端口", validator=validate_port)
            assert result == "8080"

        print("✅ 字符串输入验证正确")

    def test_input_choice(self):
        """测试选择输入"""
        wizard = ConfigWizard()

        choices = ["选项A", "选项B", "选项C"]

        # 测试有效选择
        with patch('builtins.input', return_value="2"):
            result = wizard.input_choice("提示", choices)
            assert result == "选项B"

        print("✅ 选择输入正确")

    def test_input_yes_no(self):
        """测试是/否输入"""
        wizard = ConfigWizard()

        # 测试选择"是"
        with patch('builtins.input', return_value="1"):
            result = wizard.input_yes_no("提示", default=True)
            assert result is True

        # 测试选择"否"
        with patch('builtins.input', return_value="2"):
            result = wizard.input_no("提示", default=False)
            assert result is False

        print("✅ 是/否输入正确")

    def test_generate_env_file(self):
        """测试 .env 文件生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = ConfigWizard()
            wizard.config = {
                "project_name": "测试项目",
                "environment": "development",
                "log_level": "INFO",
                "timezone": "Asia/Shanghai",
                "api_port": "8080",
                "storage_path": tmpdir,
                "database_type": "sqlite",
                "database_path": f"{tmpdir}/database.db",
                "redis_enabled": True,
                "redis_host": "localhost",
                "redis_port": "6379",
                "redis_password": "",
                "redis_db": "0",
                "scheduler_enabled": True,
                "scheduler_tick_interval": "60",
                "scheduler_max_concurrent": "5"
            }

            env_file = Path(tmpdir) / ".env"
            wizard._generate_env_file(env_file)

            # 验证文件存在
            assert env_file.exists()

            # 验证内容
            content = env_file.read_text()
            assert "PROJECT_NAME=测试项目" in content
            assert "ENVIRONMENT=development" in content
            assert "API_PORT=8080" in content
            assert "DATABASE_TYPE=sqlite" in content
            assert "REDIS_ENABLED=true" in content
            assert "SCHEDULER_ENABLED=true" in content

            print("✅ .env 文件生成正确")

    def test_generate_account_config(self):
        """测试账号配置生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = ConfigWizard()
            wizard.config_dir = Path(tmpdir) / "config"
            wizard.config_dir.mkdir(parents=True, exist_ok=True)

            wizard.config = {
                "xhs_account_id": "test_account",
                "xhs_account_name": "测试账号",
                "xhs_cookies": "test_cookie_value",
                "image_service": "stability"
            }

            wizard._generate_account_config()

            account_file = wizard.config_dir / "accounts" / "test_account.json"

            # 验证文件存在
            assert account_file.exists()

            # 验证内容
            with open(account_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["account_id"] == "test_account"
            assert data["account_name"] == "测试账号"
            assert data["platform"] == "xiaohongshu"
            assert data["cookies"]["raw"] == "test_cookie_value"

            print("✅ 账号配置生成正确")

    def test_generate_image_config(self):
        """测试图像服务配置生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = ConfigWizard()
            wizard.config_dir = Path(tmpdir) / "config"
            wizard.config_dir.mkdir(parents=True, exist_ok=True)

            wizard.config = {
                "image_service": "stability",
                "image_service_name": "Stability AI",
                "image_service_url": "https://api.stability.ai",
                "image_api_key": "sk_test_key"
            }

            wizard._generate_image_config()

            image_config_file = wizard.config_dir / "image_services.json"

            # 验证文件存在
            assert image_config_file.exists()

            # 验证内容
            with open(image_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["default_service"] == "stability"
            assert "services" in data
            assert "stability" in data["services"]
            assert data["services"]["stability"]["name"] == "Stability AI"
            assert data["services"]["stability"]["api_key"] == "sk_test_key"

            print("✅ 图像服务配置生成正确")


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试"""

    def test_full_wizard_flow(self):
        """测试完整向导流程（模拟输入）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = ConfigWizard()
            wizard.project_root = Path(tmpdir)
            wizard.config_dir = wizard.project_root / "config"
            wizard.config_dir.mkdir(parents=True, exist_ok=True)

            # 模拟用户输入
            simulated_inputs = [
                "测试项目",              # 项目名称
                "1",                     # 开发环境
                "2",                     # INFO 日志级别
                "8080",                  # API 端口
                "",                      # 时区（默认）
                "2",                     # 有账号
                "",                      # 账号 ID（默认）
                "",                      # Cookies（可选）
                "测试账号",              # 账号名称
                "1",                     # Stability AI
                "",                      # API Key（可选）
                "1",                     # SQLite
                "",                      # 存储路径（默认）
                "2",                     # 使用 Redis
                "",                      # Redis 主机（默认）
                "",                      # Redis 端口（默认）
                "2",                     # 无密码
                "",                      # Redis DB（默认）
                "1",                     # 启用调度器
                "",                      # 调度间隔（默认）
                ""                       # 并发数（默认）
            ]

            with patch('builtins.input', side_effect=simulated_inputs):
                wizard.run()

            # 验证配置文件生成
            env_file = wizard.project_root / ".env"
            assert env_file.exists()

            # 验证账号配置
            account_files = list((wizard.config_dir / "accounts").glob("*.json"))
            assert len(account_files) > 0

            # 验证图像配置
            image_config = wizard.config_dir / "image_services.json"
            assert image_config.exists()

            print("✅ 完整向导流程正确")


# ============================================================================
# 运行所有测试
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行配置向导测试...\n")

    print("="*60)
    print("测试验证函数")
    print("="*60)
    TestValidators().test_validate_required()
    TestValidators().test_validate_port()
    TestValidators().test_validate_choice()

    print("\n" + "="*60)
    print("测试配置向导")
    print("="*60)
    TestConfigWizard().test_initialization()
    TestConfigWizard().test_image_services()
    TestConfigWizard().test_input_str_with_default()
    TestConfigWizard().test_input_str_with_value()
    TestConfigWizard().test_input_str_validation()
    TestConfigWizard().test_input_choice()
    TestConfigWizard().test_generate_env_file()
    TestConfigWizard().test_generate_account_config()
    TestConfigWizard().test_generate_image_config()

    print("\n" + "="*60)
    print("测试集成")
    print("="*60)
    TestIntegration().test_full_wizard_flow()

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
