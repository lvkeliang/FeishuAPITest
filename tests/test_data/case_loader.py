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
        可以通过账号名称(name)或索引位置(index)获取

        Args:
            identifier: 可以是账号名称(str)或索引位置(int)

        Returns:
            账号信息的字典

        Raises:
            ValueError: 当找不到对应账号或索引超出范围时
        """
        accounts = self._env_config["test_groups"]

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


# 全局配置访问点
config = ConfigLoader()

# 测试用例数据类
class TestCase:
    def __init__(self, name: str, description: str, category: str, request: Dict, expected: Dict, 
                 setup: list = None, teardown: list = None):
        self.name = name
        self.description = description
        self.category = category
        self.request = TestCaseRequest(request)
        self.expected = TestCaseExpected(expected)
        self.setup = setup or []
        self.teardown = teardown or []

class TestCaseRequest:
    def __init__(self, data: Dict):
        self.data = data
    
    def dict(self):
        return self.data.copy()

class TestCaseExpected:
    def __init__(self, data: Dict):
        self.data = data
    
    def dict(self):
        return self.data.copy()

# 为了保持向后兼容，创建一个测试用例加载器类
class TestCaseLoader:
    def __init__(self):
        self.config = config
        self.test_data_dir = Path(__file__).parent
    
    def load_cases_by_type(self, category: str, msg_type: str):
        """
        根据类型加载测试用例
        
        Args:
            category: 测试类别 ("message", "history")
            msg_type: 消息类型 ("text", "image", "file" 等)
        
        Returns:
            List[TestCase]: 测试用例列表
        """
        cases = []
        case_dir = self.test_data_dir / category / msg_type
        
        if not case_dir.exists():
            return cases
        
        # 遍历 positive 和 negative 目录
        for subdir in ["positive", "negative"]:
            subdir_path = case_dir / subdir
            if subdir_path.exists():
                for case_file in subdir_path.glob("*.json"):
                    try:
                        with open(case_file, encoding='utf-8') as f:
                            case_data = yaml.safe_load(f)
                        
                        test_case = TestCase(
                            name=case_data.get("name", case_file.stem),
                            description=case_data.get("description", ""),
                            category=case_data.get("category", subdir),
                            request=case_data.get("request", {}),
                            expected=case_data.get("expected", {}),
                            setup=case_data.get("setup", []),
                            teardown=case_data.get("teardown", [])
                        )
                        cases.append(test_case)
                    except Exception as e:
                        print(f"Error loading test case from {case_file}: {e}")
        
        return cases
    
    def execute_setup(self, setup_actions: list) -> Dict[str, Any]:
        """
        执行测试用例的setup操作
        
        Args:
            setup_actions: setup操作列表
            
        Returns:
            Dict[str, Any]: 设置好的上下文变量
        """
        context = {}
        
        for action in setup_actions:
            action_type = action.get("action")
            save_to = action.get("save_to")
            
            if action_type == "get_tenant_access_token":
                # 获取真实的token
                token = self._get_real_token()
                context[save_to] = token
            elif action_type == "get_open_id":
                # 获取真实的open_id
                open_id = self.config.get_test_account(0)["open_id"]
                context[save_to] = open_id
            elif action_type == "generate_uuid":
                import uuid
                context[save_to] = str(uuid.uuid4())
            elif action_type == "load_text":
                # 加载文本文件内容
                text_path = action.get("text_path", "")
                # 修正路径分隔符
                text_path = text_path.replace("\\", "/")
                # 相对于项目根目录
                full_path = Path(text_path)
                if not full_path.is_absolute():
                    # 相对于项目根目录
                    project_root = Path(__file__).parent.parent.parent
                    full_path = project_root / text_path
                
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        context[save_to] = f.read().strip()
                except Exception as e:
                    print(f"Failed to load text from {full_path}: {e}")
                    context[save_to] = "test text content"
            elif action_type == "upload_image":
                # 上传图片并获取image_key
                image_path = action.get("image_path", "")
                image_type = action.get("image_type", "message")
                
                # 修正路径分隔符
                image_path = image_path.replace("\\", "/")
                # 相对于项目根目录
                full_path = Path(image_path)
                if not full_path.is_absolute():
                    project_root = Path(__file__).parent.parent.parent
                    full_path = project_root / image_path
                
                try:
                    # 获取上传图片的方法
                    image_key = self._upload_image_file(full_path, image_type)
                    context[save_to] = image_key
                except Exception as e:
                    print(f"Failed to upload image from {full_path}: {e}")
                    context[save_to] = "fake_image_key"
            elif action_type == "upload_file":
                # 上传文件并获取file_key
                file_path = action.get("file_path", "")
                file_type = action.get("file_type", "stream")
                file_name = action.get("file_name", None)
                
                # 修正路径分隔符
                file_path = file_path.replace("\\", "/")
                # 相对于项目根目录
                full_path = Path(file_path)
                if not full_path.is_absolute():
                    project_root = Path(__file__).parent.parent.parent
                    full_path = project_root / file_path
                
                try:
                    # 获取上传文件的方法
                    file_key = self._upload_media_file(full_path, file_type, file_name)
                    context[save_to] = file_key
                except Exception as e:
                    print(f"Failed to upload file from {full_path}: {e}")
                    context[save_to] = "fake_file_key"
            else:
                print(f"Unknown setup action: {action_type}")
        
        return context
    
    def _get_real_token(self) -> str:
        """
        获取真实的租户访问令牌
        
        Returns:
            str: 访问令牌
        """
        import requests
        
        url = f"{self.config.env_config['feishu']['base_url']}/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.config.env_config["feishu"]["app_id"],
            "app_secret": self.config.env_config["feishu"]["app_secret"]
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()["tenant_access_token"]
        except Exception as e:
            print(f"Failed to get real token: {e}")
            return "fake_token"
    
    def _upload_image_file(self, image_path: Path, image_type: str) -> str:
        """
        上传图片文件并返回image_key
        
        Args:
            image_path: 图片文件路径
            image_type: 图片类型
            
        Returns:
            str: 图片的image_key
        """
        import requests
        from requests_toolbelt import MultipartEncoder
        
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        url = f"{self.config.env_config['feishu']['base_url']}/open-apis/im/v1/images"
        
        # 使用 MultipartEncoder 构造请求体
        multipart_form = MultipartEncoder(
            fields={
                'image_type': image_type,
                'image': (image_path.name, open(image_path, 'rb'), 'image/jpeg')
            }
        )
        
        headers = {
            "Authorization": f"Bearer {self._get_real_token()}",
            'Content-Type': multipart_form.content_type
        }
        
        with open(image_path, 'rb'):
            response = requests.post(
                url,
                headers=headers,
                data=multipart_form,
                timeout=30
            )
        
        response.raise_for_status()
        response_data = response.json()
        if response_data.get('code') != 0:
            raise Exception(f"Upload image failed: {response_data.get('msg')}")
        
        return response_data['data']['image_key']
    
    def _upload_media_file(self, file_path: Path, file_type: str, file_name: str = None) -> str:
        """
        上传媒体文件并返回file_key
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            file_name: 文件名
            
        Returns:
            str: 文件的file_key
        """
        import requests
        from mimetypes import guess_type
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # 自动检测 MIME 类型
        mime_type, _ = guess_type(file_path.name)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        url = f"{self.config.env_config['feishu']['base_url']}/open-apis/im/v1/files"
        
        # 准备表单数据
        form_data = {
            'file_type': (None, file_type),
            'file_name': (None, file_name or file_path.name),
            'file': (file_path.name, open(file_path, 'rb'), mime_type)
        }
        
        headers = {
            "Authorization": f"Bearer {self._get_real_token()}",
        }
        
        response = requests.post(
            url=url,
            headers=headers,
            files=form_data,
            timeout=30
        )
        
        response.raise_for_status()
        response_data = response.json()
        if response_data.get('code') != 0:
            raise Exception(f"Upload file failed: {response_data.get('msg')}")
        
        return response_data['data']['file_key']
    
    def replace_variables(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        替换数据中的变量占位符
        
        Args:
            data: 需要替换变量的数据
            context: 变量上下文
            
        Returns:
            Dict[str, Any]: 替换后的数据
        """
        import json
        
        # 深拷贝数据以避免修改原始数据
        result = json.loads(json.dumps(data))
        
        # 递归替换变量
        result = self._replace_variables_recursive(result, context)
        
        # 处理特殊的 JSON 编码需求
        result = self._process_json_encoding(result)
        
        return result
    
    def _replace_variables_recursive(self, obj: Any, context: Dict[str, Any]) -> Any:
        """
        递归替换变量占位符
        """
        if isinstance(obj, dict):
            return {k: self._replace_variables_recursive(v, context) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_variables_recursive(item, context) for item in obj]
        elif isinstance(obj, str):
            # 替换字符串中的变量占位符
            for key, value in context.items():
                obj = obj.replace(f"${key}$", str(value))
            return obj
        else:
            return obj
    
    def _process_json_encoding(self, obj: Any) -> Any:
        """
        处理需要 JSON 编码的字段
        """
        import json
        
        if isinstance(obj, dict):
            if obj.get("__needs_json_encode"):
                # 移除标志字段并 JSON 编码内容
                content = {k: v for k, v in obj.items() if k != "__needs_json_encode"}
                return json.dumps(content)
            else:
                return {k: self._process_json_encoding(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._process_json_encoding(item) for item in obj]
        else:
            return obj
    
    def execute_teardown(self, teardown_actions: list, response_data: Dict[str, Any]):
        """
        执行测试用例的teardown操作
        
        Args:
            teardown_actions: teardown操作列表
            response_data: 响应数据
        """
        for action in teardown_actions:
            action_type = action.get("action")
            
            if action_type == "delete_message":
                # 这里应该实现删除消息的逻辑
                print(f"Teardown: delete_message (placeholder)")
            else:
                print(f"Unknown teardown action: {action_type}")

# 全局测试用例加载器访问点
test_case_loader = TestCaseLoader()