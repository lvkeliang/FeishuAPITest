import json
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
import pytest
from pydantic import BaseModel, validator
from tests.client.client import feishu_client
from tests.utils.config_loader import config


class RequestModel(BaseModel):
    """请求数据模型"""
    method: str
    endpoint: str
    query_params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None


class ExpectedModel(BaseModel):
    """预期响应数据模型"""
    status_code: int
    headers: Optional[Dict[str, Any]] = None
    schema: Optional[str] = None
    body: Optional[Dict[str, Any]] = None


class TestCaseModel(BaseModel):
    """完整测试用例数据模型"""
    name: str
    description: Optional[str] = None
    category: str
    request: RequestModel
    expected: ExpectedModel
    setup: Optional[List[Dict[str, Any]]] = None
    teardown: Optional[List[Dict[str, Any]]] = None


class TestCaseLoader:
    """测试用例加载器"""

    def __init__(self, base_path: str = "tests/test_data"):
        self.base_path = Path(base_path)
        self._context = {}  # 存储测试上下文数据

    def load_case(self, case_path: str) -> TestCaseModel:
        """加载单个测试用例文件"""
        case_file = self.base_path / case_path
        if not case_file.exists():
            raise FileNotFoundError(f"测试用例文件不存在: {case_file}")

        case_data = json.loads(case_file.read_text(encoding='utf-8'))
        return TestCaseModel(**case_data)

    def load_cases_by_type(self, api_name: str, test_type: str) -> List[TestCaseModel]:
        """加载指定API和消息类型的所有测试用例"""
        api_path = self.base_path / api_name / test_type
        if not api_path.exists():
            raise ValueError(f"消息类型目录不存在: {api_path}")

        cases = []

        # 加载正例
        positive_dir = api_path / "positive"
        if positive_dir.exists():
            cases.extend(self._load_cases_from_dir(positive_dir, "positive"))

        # 加载反例
        negative_dir = api_path / "negative"
        if negative_dir.exists():
            cases.extend(self._load_cases_from_dir(negative_dir, "negative"))

        return cases

    def _load_cases_from_dir(self, case_dir: Path, category: str) -> List[TestCaseModel]:
        """从目录加载所有测试用例"""
        cases = []
        for case_file in case_dir.glob("*.json"):
            try:
                case_data = json.loads(case_file.read_text(encoding='utf-8'))
                case_data["category"] = category
                cases.append(TestCaseModel(**case_data))
            except Exception as e:
                pytest.fail(f"加载测试用例失败 {case_file}: {str(e)}")
        return cases

    def execute_setup(self, setup_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行setup操作并返回上下文数据"""
        context = {}

        for action in setup_actions:
            action_type = action["action"]

            if action_type == "get_tenant_access_token":
                # 实际获取token的逻辑
                context[action["save_to"]] = feishu_client.tenant_access_token

            elif action_type == "get_open_id":
                context[action["save_to"]] = config.get_test_account(0)["open_id"]

            elif action_type == "generate_uuid":
                context[action["save_to"]] = str(uuid.uuid4())

            elif action_type == "upload_image":
                # 图片上传逻辑
                context[action["save_to"]] = feishu_client.upload_image(action["image_path"], action["image_type"])

            elif action_type == "load_and_dump_json":
                json_file_path = Path(action["json_path"])
                context[action["save_to"]] = json.dumps(json.loads(json_file_path.read_text(encoding='utf-8')), ensure_ascii=False)
                print(json.loads(json_file_path.read_text(encoding='utf-8')))
                print()
                print(json.dumps(json.loads(json_file_path.read_text(encoding='utf-8')), ensure_ascii=False))

            elif action_type == "load_text":
                file_path = Path(action["text_path"])
                context[action["save_to"]] = file_path.read_text(encoding='utf-8')

            elif action_type == "get_chat_id":
                context[action["save_to"]] = config.get_test_account(0)["chat_id"]


            # 可以添加更多setup操作

            # 将结果保存到指定变量
            if "save_to" in action:
                self._context[action["save_to"]] = context.get(action["save_to"])

        return context

    def execute_teardown(self, teardown_actions: List[Dict[str, Any]], response: Dict[str, Any]):
        """执行teardown操作"""
        for action in teardown_actions:
            action_type = action["action"]

            if action_type == "delete_message":
                # 实际删除消息的逻辑
                message_id = self.replace_variables(action["params"], response)["message_id"]
                print(f"Cleaning up message: {message_id}")

            # 可以添加更多teardown操作

    def replace_variables(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        三阶段变量处理：
        1. 识别需要JSON编码的字段（不修改内容）
        2. 执行深层变量替换
        3. 对标记字段进行JSON编码
        """
        # 第一阶段：标记需要JSON编码的字段
        needs_encode, marked_data = self._mark_encode_fields(data)

        # 第二阶段：深度变量替换
        replaced_data = self._deep_replace_variables(marked_data, context)

        # 第三阶段：执行JSON编码
        return self._apply_json_encoding(replaced_data, needs_encode)

    def _mark_encode_fields(self, data: Any) -> tuple[set, Any]:
        """递归标记需要JSON编码的字段路径"""
        if isinstance(data, dict):
            needs_encode = set()
            marked_data = {}
            for k, v in data.items():
                child_needs, child_marked = self._mark_encode_fields(v)
                needs_encode.update(f"{k}.{path}" for path in child_needs)
                # if k.endswith('_json') and isinstance(v, (dict, list)):
                if k.endswith('_json') and isinstance(v, (dict, list)):
                    needs_encode.add(k)
                elif isinstance(v, dict) and v.get('__needs_json_encode'):
                    needs_encode.add(k)
                marked_data[k] = child_marked
            return needs_encode, marked_data
        elif isinstance(data, list):
            needs_encode = set()
            marked_data = []
            for i, v in enumerate(data):
                child_needs, child_marked = self._mark_encode_fields(v)
                needs_encode.update(f"[{i}].{path}" for path in child_needs)
                marked_data.append(child_marked)
            return needs_encode, marked_data
        return set(), data

    def _deep_replace_variables(self, data: Any, context: Dict[str, Any]) -> Any:
        """纯变量替换（不处理JSON编码）"""
        if isinstance(data, dict):
            return {k: self._deep_replace_variables(v, context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._deep_replace_variables(v, context) for v in data]
        elif isinstance(data, str):
            return self._process_string_variables(data, context)
        return data

    def _apply_json_encoding(self, data: Any, needs_encode: set, current_path: str = "") -> Any:
        """根据标记执行JSON编码"""
        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                new_path = f"{current_path}.{k}" if current_path else k
                # 在编码前深度清理元数据
                if isinstance(v, dict):
                    v = {
                        key: val
                        for key, val in v.items()
                        if key != '__needs_json_encode'
                    }
                if new_path in needs_encode:
                    result[k.rstrip('_json')] = json.dumps(v, ensure_ascii=False)
                else:
                    result[k] = self._apply_json_encoding(v, needs_encode, new_path)
            return result
        elif isinstance(data, list):
            return [
                self._apply_json_encoding(
                    v,
                    needs_encode,
                    f"{current_path}[{i}]"
                )
                for i, v in enumerate(data)
            ]
        return data

    def _process_string_variables(self, text: str, context: Dict[str, Any]) -> str:
        """处理字符串中的变量（保留原有逻辑）"""
        if text.startswith("$") and text.endswith("$"):
            return self._replace_explicit_variable(text[1:-1], context)
        return self._replace_embedded_variables(text, context)

    def _replace_explicit_variable(self, var_name: str, context: Dict[str, Any]) -> Any:
        """处理显式变量引用：$var$ 或 $response.data.field$"""
        if var_name.startswith("response."):
            parts = var_name.split(".")[1:]  # 去掉response前缀
            value = context
            for part in parts:
                value = value.get(part, {})
            return value
        return self._context.get(var_name, f"${var_name}$")  # 保持原格式若未找到

    def _replace_embedded_variables(self, text: str, context: Dict[str, Any]) -> str:
        """处理字符串内嵌变量：如 "Prefix_$var$_Suffix" """
        return re.sub(
            r'\$([a-zA-Z_][a-zA-Z0-9_]*)\$',
            lambda m: str(self._context.get(m.group(1), m.group(0))),
            text
        )

    def _resolve_field_path(self, path: str) -> Any:
        """解析字段路径（如 request.body.content）获取值"""
        parts = path.split('.')
        data = self._context
        for part in parts:
            data = data.get(part, {})
        return data

    def _set_field_path(self, path: str, value: Any):
        """设置字段路径的值"""
        parts = path.split('.')
        data = self._context
        for part in parts[:-1]:
            if part not in data:
                data[part] = {}
            data = data[part]
        data[parts[-1]] = value


# 全局测试用例加载器实例
test_case_loader = TestCaseLoader()
