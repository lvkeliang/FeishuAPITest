import os
import yaml
from pathlib import Path
from typing import Dict, Any

class ConfigLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载所有配置文件"""
        config_dir = Path(__file__).parent.parent.parent / "config"

        # 加载主配置
        with open(config_dir / "feishu_config.yaml", encoding='utf-8') as f:
            self._config = yaml.safe_load(f)

        # 加载环境配置
        env_file = config_dir / "test_env" / f"{self._config['base']['default_env']}.yaml"
        with open(env_file, encoding='utf-8') as f:
            self._env_config = yaml.safe_load(f)

    @property
    def config(self) -> Dict[str, Any]:
        """获取主配置"""
        return self._config

    @property
    def env_config(self) -> Dict[str, Any]:
        """获取环境配置"""
        return self._env_config

    def get_test_account(self, name: str) -> Dict[str, str]:
        """获取测试账号信息"""
        for account in self._env_config["test_accounts"]:
            if account["name"] == name:
                return account
        raise ValueError(f"Test account '{name}' not found")


# 全局配置访问点
config = ConfigLoader()