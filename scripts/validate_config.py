#!/usr/bin/env python3
"""
配置验证和安全加固脚本

检查配置文件权限，验证API密钥，并提供修复建议。
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.security import (
    key_manager,
    validate_config_permissions,
    validate_api_key
)


class ConfigValidator:
    """配置验证器"""

    def __init__(self, base_dir: Path):
        """
        初始化验证器

        Args:
            base_dir: 项目根目录
        """
        self.base_dir = base_dir
        self.results = []
        self.config_files = [
            base_dir / "xhs-operator" / "CONFIG" / "accounts.json",
            base_dir / "xhs-operator" / "CONFIG" / "templates.json",
            base_dir / "xhs-operator" / "CONFIG" / "schedule.yaml",
            base_dir / "xhs-operator" / "CONFIG" / "image_models.json",
        ]

    def validate_all(self) -> Dict[str, Any]:
        """
        执行所有验证检查

        Returns:
            验证结果摘要
        """
        print("🔍 开始配置验证...\n")

        # 1. 检查文件权限
        print("📁 检查文件权限...")
        permission_results = self._check_permissions()

        # 2. 检查API密钥
        print("\n🔑 检查API密钥...")
        key_results = self._check_api_keys()

        # 3. 检查配置文件格式
        print("\n📄 检查配置文件格式...")
        format_results = self._check_format()

        # 4. 生成报告
        return self._generate_report(permission_results, key_results, format_results)

    def _check_permissions(self) -> List[Dict[str, Any]]:
        """检查文件权限"""
        results = []

        for config_file in self.config_files:
            if config_file.exists():
                result = validate_config_permissions(config_file)
                results.append(result)

                if result["secure"]:
                    print(f"  ✅ {config_file.name}")
                else:
                    print(f"  ⚠️  {config_file.name}")
                    for issue in result["issues"]:
                        print(f"      - {issue}")
            else:
                print(f"  ❓ {config_file.name} (不存在)")
                results.append({
                    "path": str(config_file),
                    "exists": False,
                    "secure": False,
                    "issues": ["File does not exist"]
                })

        return results

    def _check_api_keys(self) -> Dict[str, Any]:
        """检查API密钥"""
        results = {
            "keys": {},
            "configured": 0,
            "valid": 0,
            "issues": []
        }

        keys_to_check = [
            "STABILITY_API_KEY",
            "OPENAI_API_KEY",
            "REPLICATE_API_TOKEN",
            "HUGGINGFACE_API_KEY",
            "IDEOGRAM_API_KEY",
            "LEONARDO_API_KEY"
        ]

        for key_name in keys_to_check:
            validation = validate_api_key(key_name)

            results["keys"][key_name] = validation

            if validation["valid"]:
                results["configured"] += 1
                results["valid"] += 1
                print(f"  ✅ {key_name}: {validation['format']} (有效)")
            else:
                if validation.get("format") != "unknown":
                    results["configured"] += 1
                    print(f"  ⚠️  {key_name}: {validation.get('format', 'Unknown')} (无效)")
                    for issue in validation["issues"]:
                        results["issues"].append(f"{key_name}: {issue}")
                else:
                    print(f"  ❌ {key_name}: 未配置")

        return results

    def _check_format(self) -> List[Dict[str, Any]]:
        """检查配置文件格式"""
        results = []

        for config_file in self.config_files:
            if not config_file.exists():
                continue

            result = {
                "file": str(config_file),
                "valid": False,
                "issues": []
            }

            try:
                if config_file.suffix in [".json"]:
                    with open(config_file, 'r') as f:
                        json.load(f)
                    result["valid"] = True
                    print(f"  ✅ {config_file.name} (有效JSON)")

                elif config_file.suffix in [".yaml", ".yml"]:
                    import yaml
                    with open(config_file, 'r') as f:
                        yaml.safe_load(f)
                    result["valid"] = True
                    print(f"  ✅ {config_file.name} (有效YAML)")

            except json.JSONDecodeError as e:
                result["issues"].append(f"Invalid JSON: {e}")
                print(f"  ❌ {config_file.name} (无效JSON: {e})")

            except Exception as e:
                result["issues"].append(f"Error: {e}")
                print(f"  ❌ {config_file.name} (错误: {e})")

            results.append(result)

        return results

    def _generate_report(
        self,
        permission_results: List[Dict[str, Any]],
        key_results: Dict[str, Any],
        format_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成验证报告"""
        # 统计问题
        total_files = len(self.config_files)
        secure_files = sum(1 for r in permission_results if r.get("secure"))
        valid_formats = sum(1 for r in format_results if r.get("valid"))

        total_issues = 0
        for r in permission_results:
            total_issues += len(r.get("issues", []))
        for r in format_results:
            total_issues += len(r.get("issues", []))
        total_issues += len(key_results.get("issues", []))

        # 计算评分
        score = 0
        if secure_files >= total_files * 0.8:
            score += 30
        elif secure_files >= total_files * 0.5:
            score += 15

        if key_results["valid"] >= 4:
            score += 40
        elif key_results["valid"] >= 2:
            score += 20

        if valid_formats >= total_files * 0.8:
            score += 30
        elif valid_formats >= total_files * 0.5:
            score += 15

        print(f"\n{'='*60}")
        print(f"📊 验证结果摘要")
        print(f"{'='*60}")
        print(f"文件权限: {secure_files}/{total_files} 安全")
        print(f"API密钥: {key_results['valid']}/{len(key_results['keys'])} 有效")
        print(f"文件格式: {valid_formats}/{total_files} 正确")
        print(f"发现问题: {total_issues} 个")
        print(f"安全评分: {score}/100")

        if score >= 80:
            print(f"状态: ✅ 良好")
        elif score >= 50:
            print(f"状态: ⚠️  需要改进")
        else:
            print(f"状态: ❌ 需要立即修复")

        print(f"{'='*60}\n")

        return {
            "score": score,
            "secure_files": secure_files,
            "total_files": total_files,
            "valid_keys": key_results["valid"],
            "total_keys": len(key_results["keys"]),
            "valid_formats": valid_formats,
            "total_issues": total_issues,
            "details": {
                "permissions": permission_results,
                "keys": key_results,
                "formats": format_results
            }
        }

    def fix_permissions(self) -> None:
        """修复文件权限"""
        print("🔧 修复文件权限...\n")

        for config_file in self.config_files:
            if config_file.exists():
                try:
                    # 设置为 600 (owner read/write only)
                    subprocess.run(
                        ["chmod", "600", str(config_file)],
                        check=True
                    )
                    print(f"  ✅ 已修复: {config_file.name}")
                except Exception as e:
                    print(f"  ❌ 修复失败: {config_file.name} - {e}")

    def generate_env_template(self) -> None:
        """生成环境变量模板"""
        env_file = self.base_dir / ".env.template"

        template = """# 小红书 AI 运营系统 - 环境变量配置
# 请复制此文件为 .env 并填入你的API密钥

# Stability AI (图像生成)
# 获取地址: https://platform.stability.ai/
STABILITY_API_KEY=sk-your-stability-api-key-here

# OpenAI DALL-E (图像生成)
# 获取地址: https://platform.openai.com/
OPENAI_API_KEY=sk-your-openai-api-key-here

# Replicate (图像生成)
# 获取地址: https://replicate.com/
REPLICATE_API_TOKEN=r8-your-replicate-token-here

# Hugging Face (图像生成 - 可选)
# 获取地址: https://huggingface.co/
HUGGINGFACE_API_KEY=hf-your-huggingface-key-here

# Ideogram (图像生成 - 可选)
# 获取地址: https://ideogram.ai/
IDEOGRAM_API_KEY=your-ideogram-api-key-here

# Leonardo AI (图像生成 - 可选)
# 获取地址: https://leonardo.ai/
LEONARDO_API_KEY=your-leonardo-api-key-here

# Tavily (内容搜索 - 可选)
# 获取地址: https://tavily.com/
TAVILY_API_KEY=tvly-your-tavily-api-key-here

# 加密密钥（可选，用于配置文件加密）
# 如果不设置，将基于机器特征自动生成
XHS_ENCRYPTION_KEY=your-32-character-encryption-key-here
"""

        env_file.write_text(template)
        print(f"\n✅ 环境变量模板已生成: {env_file}")
        print(f"   请复制为 .env 并填入你的API密钥")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="配置验证和安全加固工具")
    parser.add_argument("--fix", action="store_true", help="自动修复权限问题")
    parser.add_argument("--template", action="store_true", help="生成环境变量模板")
    parser.add_argument("--base-dir", type=Path, default=Path.cwd(), help="项目根目录")

    args = parser.parse_args()

    validator = ConfigValidator(args.base_dir)

    # 执行验证
    report = validator.validate_all()

    # 自动修复权限
    if args.fix:
        validator.fix_permissions()

    # 生成环境变量模板
    if args.template:
        validator.generate_env_template()

    # 返回退出码
    if report["score"] >= 80:
        return 0
    elif report["score"] >= 50:
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
