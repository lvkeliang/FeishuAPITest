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

    def get_test_account(self, identifier: str | int) -> Dict[str, str]:
        """获取测试账号信息
        可以通过账号名称(name)或索引位置(index)获取

        Args:
            identifier: 可以是账号名称(str)或索引位置(int)

        Returns:
            账号信息的字典

        Raises:
            ValueError: 当找不到对应账号或索引超出范围时
        """
        accounts = self._env_config["test_accounts"]

        if isinstance(identifier, int):
            # 通过索引获取
            if 0 <= identifier < len(accounts):
                return accounts[identifier]
            raise ValueError(f"Test account index {identifier} out of range (0-{len(accounts) - 1})")
        elif isinstance(identifier, str):
            # 通过名称获取
            for account in accounts:
                if account["name"] == identifier:
                    return account
            raise ValueError(f"Test account '{identifier}' not found")
        else:
            raise TypeError("Identifier must be either int (index) or str (name)")

    def get_test_group(self, identifier: str | int) -> Dict[str, str]:
        """获取测试群组信息
        可以通过群组名称(name)或索引位置(index)获取

        Args:
            identifier: 可以是群组名称(str)或索引位置(int)

        Returns:
            账号信息的字典

        Raises:
            ValueError: 当找不到对应群组或索引超出范围时
        """
        accounts = self._env_config["test_groups"]

        if isinstance(identifier, int):
            # 通过索引获取
            if 0 <= identifier < len(accounts):
                return accounts[identifier]
            raise ValueError(f"Test group index {identifier} out of range (0-{len(accounts) - 1})")
        elif isinstance(identifier, str):
            # 通过名称获取
            for account in accounts:
                if account["name"] == identifier:
                    return account
            raise ValueError(f"Test group '{identifier}' not found")
        else:
            raise TypeError("Identifier must be either int (index) or str (name)")

    def get_test_thread(self, identifier: str | int) -> Dict[str, str]:
        """获取测试话题信息
        可以通过话题名称(name)或索引位置(index)获取

        Args:
            identifier: 可以是话题名称(str)或索引位置(int)

        Returns:
            账号信息的字典

        Raises:
            ValueError: 当找不到对应话题或索引超出范围时
        """
        accounts = self._env_config["test_threads"]

        if isinstance(identifier, int):
            # 通过索引获取
            if 0 <= identifier < len(accounts):
                return accounts[identifier]
            raise ValueError(f"Test thread index {identifier} out of range (0-{len(accounts) - 1})")
        elif isinstance(identifier, str):
            # 通过名称获取
            for account in accounts:
                if account["name"] == identifier:
                    return account
            raise ValueError(f"Test thread '{identifier}' not found")
        else:
            raise TypeError("Identifier must be either int (index) or str (name)")




# 全局配置访问点
config = ConfigLoader()
