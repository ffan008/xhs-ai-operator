#!/usr/bin/env python3
"""
小红书 AI 运营系统 - 图像模型管理器
支持多个图像生成模型的统一接口
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger("image-model-manager")


class ModelStrategy(str, Enum):
    """模型选择策略"""
    COST_FIRST = "cost_first"  # 优先使用便宜的
    QUALITY_FIRST = "quality_first"  # 优先使用质量高的
    SPEED_FIRST = "speed_first"  # 优先使用速度快的
    BALANCED = "balanced"  # 平衡模式


class ImageModelManager:
    """图像生成模型管理器"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化模型管理器

        Args:
            config_path: 模型配置文件路径
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "xhs-operator" / "CONFIG" / "image_models.json"

        self.config_path = config_path
        self.config = self._load_config()
        self.enabled_models = self._get_enabled_models()

    def _load_config(self) -> Dict[str, Any]:
        """加载模型配置"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "default_model": "stability",
            "models": {
                "stability": {
                    "name": "Stability AI",
                    "enabled": True,
                    "models": {
                        "sd3": {"name": "Stable Diffusion 3", "model_id": "sd3"}
                    }
                }
            }
        }

    def _get_enabled_models(self) -> Dict[str, Any]:
        """获取已启用的模型"""
        enabled = {}
        for model_id, model_config in self.config.get("models", {}).items():
            if model_config.get("enabled", False):
                enabled[model_id] = model_config
        return enabled

    def list_models(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """
        列出所有模型

        Args:
            include_disabled: 是否包含已禁用的模型

        Returns:
            模型列表
        """
        models = []
        for model_id, model_config in self.config.get("models", {}).items():
            if not model_config.get("enabled", False) and not include_disabled:
                continue

            models.append({
                "id": model_id,
                "name": model_config.get("name"),
                "provider": model_config.get("provider"),
                "enabled": model_config.get("enabled", False),
                "submodels": list(model_config.get("models", {}).keys()),
                "default_model": model_config.get("default_model"),
                "cost_estimate": model_config.get("cost_estimate", {}),
                "api_key_required": model_config.get("api_key_required", False)
            })

        return models

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        获取特定模型配置

        Args:
            model_id: 模型ID

        Returns:
            模型配置或None
        """
        return self.config.get("models", {}).get(model_id)

    def select_model(
        self,
        strategy: Optional[ModelStrategy] = None,
        preferred_model: Optional[str] = None,
        aspect_ratio: str = "3:4"
    ) -> Optional[Dict[str, Any]]:
        """
        根据策略选择合适的模型

        Args:
            strategy: 选择策略
            preferred_model: 首选模型
            aspect_ratio: 所需的图片比例

        Returns:
            选择的模型配置
        """
        # 如果指定了首选模型，优先使用
        if preferred_model:
            model = self.get_model(preferred_model)
            if model and model.get("enabled", False):
                logger.info(f"Using preferred model: {preferred_model}")
                return self._select_submodel(model, aspect_ratio)
            else:
                logger.warning(f"Preferred model {preferred_model} not available or disabled")

        # 使用配置的策略
        if strategy is None:
            strategy = ModelStrategy(self.config.get("model_selection_strategy", "cost_first"))

        # 根据策略选择模型
        if strategy == ModelStrategy.COST_FIRST:
            ranking = self.config.get("cost_ranking", [])
        elif strategy == ModelStrategy.QUALITY_FIRST:
            ranking = self.config.get("quality_ranking", [])
        elif strategy == ModelStrategy.SPEED_FIRST:
            ranking = self.config.get("speed_ranking", [])
        else:  # BALANCED
            ranking = self.config.get("fallback_order", [])

        # 按排名查找第一个可用的模型
        for model_id in ranking:
            model = self.get_model(model_id)
            if model and model.get("enabled", False):
                logger.info(f"Selected model: {model_id} (strategy: {strategy})")
                return self._select_submodel(model, aspect_ratio)

        # 如果没有找到，使用默认模型
        default_id = self.config.get("default_model", "stability")
        model = self.get_model(default_id)
        if model and model.get("enabled", False):
            logger.info(f"Using default model: {default_id}")
            return self._select_submodel(model, aspect_ratio)

        logger.error("No available model found")
        return None

    def _select_submodel(
        self,
        model: Dict[str, Any],
        aspect_ratio: str
    ) -> Dict[str, Any]:
        """
        选择模型的特定子模型

        Args:
            model: 模型配置
            aspect_ratio: 所需的图片比例

        Returns:
            完整的模型配置（包含子模型）
        """
        submodels = model.get("models", {})
        default_submodel_id = model.get("default_model")

        # 优先使用默认子模型
        if default_submodel_id and default_submodel_id in submodels:
            submodel = submodels[default_submodel_id]
            # 检查是否支持所需比例
            if aspect_ratio in submodel.get("supported_ratios", [aspect_ratio]):
                return {
                    **model,
                    "selected_submodel": default_submodel_id,
                    "submodel_config": submodel
                }

        # 查找支持该比例的第一个子模型
        for submodel_id, submodel_config in submodels.items():
            if aspect_ratio in submodel_config.get("supported_ratios", [aspect_ratio]):
                return {
                    **model,
                    "selected_submodel": submodel_id,
                    "submodel_config": submodel_config
                }

        # 如果都不支持，使用默认子模型
        if default_submodel_id and default_submodel_id in submodels:
            return {
                **model,
                "selected_submodel": default_submodel_id,
                "submodel_config": submodels[default_submodel_id]
            }

        # 使用第一个可用的子模型
        first_submodel_id = list(submodels.keys())[0]
        return {
            **model,
            "selected_submodel": first_submodel_id,
            "submodel_config": submodels[first_submodel_id]
        }

    def get_model_params(
        self,
        model_config: Dict[str, Any],
        prompt: str,
        aspect_ratio: str = "3:4",
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成调用模型所需的参数

        Args:
            model_config: 模型配置
            prompt: 图像生成提示词
            aspect_ratio: 图片比例
            **kwargs: 额外参数

        Returns:
            模型调用参数
        """
        submodel_config = model_config.get("submodel_config", {})
        provider = model_config.get("provider", "")
        api_type = model_config.get("api_type", "")

        params = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio
        }

        # 根据不同的API类型添加特定参数
        if api_type == "stability":
            params.update({
                "model": submodel_config.get("model_id"),
                "steps": kwargs.get("steps", submodel_config.get("max_steps", 30)),
                "cfg_scale": kwargs.get("cfg_scale", 7.5),
                "samples": 1
            })

        elif api_type == "openai":
            params.update({
                "model": submodel_config.get("model_id"),
                "quality": kwargs.get("quality", submodel_config.get("quality", "standard")),
                "style": kwargs.get("style", submodel_config.get("style", "vivid")),
                "size": self._get_openai_size(aspect_ratio)
            })

        elif api_type == "replicate":
            params.update({
                "model": submodel_config.get("model_id"),
                "num_outputs": 1
            })

        elif api_type == "huggingface":
            params.update({
                "model": submodel_config.get("model_id"),
                "parameters": {
                    "num_inference_steps": kwargs.get("steps", 20)
                }
            })

        # 添加自定义参数
        params.update(kwargs)

        return params

    def _get_openai_size(self, aspect_ratio: str) -> str:
        """将比例转换为OpenAI的size格式"""
        ratio_map = {
            "1:1": "1024x1024",
            "3:4": "1024x1365",
            "4:3": "1365x1024"
        }
        return ratio_map.get(aspect_ratio, "1024x1024")

    def estimate_cost(self, model_id: str, submodel_id: Optional[str] = None) -> Optional[str]:
        """
        估算生成成本

        Args:
            model_id: 模型ID
            submodel_id: 子模型ID（可选）

        Returns:
            成本估算字符串
        """
        model = self.get_model(model_id)
        if not model:
            return None

        cost_estimate = model.get("cost_estimate", {})

        if submodel_id:
            return cost_estimate.get(submodel_id)

        # 返回默认子模型的成本
        default_submodel = model.get("default_model")
        if default_submodel:
            return cost_estimate.get(default_submodel)

        # 返回成本范围
        if cost_estimate:
            values = list(cost_estimate.values())
            if values:
                return f"{min(values)} - {max(values)}"

        return None

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        更新配置文件

        Args:
            new_config: 新配置

        Returns:
            是否成功
        """
        try:
            # 保存到文件
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, ensure_ascii=False, indent=2)

            # 更新内存中的配置
            self.config = new_config
            self.enabled_models = self._get_enabled_models()

            logger.info("Model configuration updated successfully")
            return True

        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return False

    def enable_model(self, model_id: str) -> bool:
        """
        启用模型

        Args:
            model_id: 模型ID

        Returns:
            是否成功
        """
        model = self.config.get("models", {}).get(model_id)
        if not model:
            logger.error(f"Model {model_id} not found")
            return False

        model["enabled"] = True
        return self.update_config(self.config)

    def disable_model(self, model_id: str) -> bool:
        """
        禁用模型

        Args:
            model_id: 模型ID

        Returns:
            是否成功
        """
        model = self.config.get("models", {}).get(model_id)
        if not model:
            logger.error(f"Model {model_id} not found")
            return False

        model["enabled"] = False
        return self.update_config(self.config)

    def get_api_requirements(self) -> List[Dict[str, str]]:
        """
        获取所有需要的API密钥信息

        Returns:
            API需求列表
        """
        requirements = []

        for model_id, model_config in self.config.get("models", {}).items():
            if model_config.get("enabled", False) and model_config.get("api_key_required", False):
                requirements.append({
                    "model": model_id,
                    "name": model_config.get("name"),
                    "env_var": model_config.get("api_key_env"),
                    "provider": model_config.get("provider")
                })

        return requirements
