import allure
import pytest
from typing import Dict, Any
from tests.client.client import feishu_client
from tests.test_data.case_loader import test_case_loader
from tests.utils.config_loader import config


@pytest.fixture(scope="module")
def client():
    """共享的Feishu客户端fixture"""
    return feishu_client


@pytest.fixture
def prepared_test_case(request):
    """准备测试用例，执行setup并替换变量"""
    loader = test_case_loader
    test_case = request.param  # 从参数化获取测试用例

    # 1. 执行setup操作
    if test_case.setup:
        setup_context = loader.execute_setup(test_case.setup)
    else:
        setup_context = {}

    # 2. 替换请求中的变量
    # context = {"open_id": test_user["open_id"], **setup_context}
    context = {**setup_context}
    replaced_request = loader.replace_variables(test_case.request.dict(), context)

    yield {
        "request": replaced_request,
        "expected": test_case.expected.dict(),
        "context": context,
        "original_case": test_case
    }

    # 3. 测试结束后执行teardown
    if hasattr(request, "node") and hasattr(request.node, "funcargs"):
        response = request.node.funcargs.get("api_response")
        if response and test_case.teardown:
            loader.execute_teardown(test_case.teardown, response.json())


# 具体消息类型的测试
def test_text_messages(client, prepared_test_case, receiver_info):
    _generic_message_test(feishu_client, prepared_test_case, receiver_info)


def test_image_messages(client, prepared_test_case, receiver_info):
    _generic_message_test(feishu_client, prepared_test_case, receiver_info)


def test_post_messages(client, prepared_test_case, receiver_info):
    _generic_message_test(feishu_client, prepared_test_case, receiver_info)


def test_interactive_messages(client, prepared_test_case, receiver_info):
    _generic_message_test(feishu_client, prepared_test_case, receiver_info)


# def test_file_messages(client, prepared_test_case):
#     _generic_message_test(feishu_client, prepared_test_case)


def _generic_message_test(client, prepared_test_case, receiver_info):
    receive_id_type, receive_id = receiver_info
    """通用消息发送测试"""
    with allure.step("Step 1: 准备测试用例"):
        test_data = prepared_test_case
        request_data = test_data["request"]

        # --- 关键修改：动态注入参数 ---
        # 1. 注入 receive_id_type 到查询参数
        query_params = request_data.get("query_params", {})
        query_params["receive_id_type"] = receive_id_type  # 覆盖或新增

        # 2. 注入 receive_id 到请求体
        request_body = request_data.get("body", {})
        request_body["receive_id"] = receive_id  # 覆盖或新增

    with allure.step("Step 2: 发送请求"):
        response = client.request(
            method=request_data["method"],
            endpoint=request_data["endpoint"],
            params=query_params,  # 使用修改后的查询参数
            headers=request_data.get("headers"),
            json=request_body  # 使用修改后的请求体
        )

    # 将响应保存到测试上下文中，供teardown使用
    pytest.api_response = response

    with allure.step("Step 3: 验证响应"):
        # 验证响应
        expected = test_data["expected"]

        # 1. 验证状态码
        assert response.status_code == expected["status_code"], \
            f"状态码不匹配，期望 {expected['status_code']}，实际 {response.status_code}"

        # 2. 验证响应头
        # if expected.get("headers"):
        #     for header, value in expected["headers"].items():
        #         assert header in response.headers, f"缺少响应头 {header}"
        #         assert response.headers[header] == value, \
        #             f"响应头 {header} 不匹配，期望 {value}，实际 {response.headers[header]}"

        # 3. 验证响应体
        # response_json = response.json()

        # 3.1 验证schema
        # if expected.get("schema"):
        #     validate_schema(response_json, expected["schema"])

        # 3.2 验证具体字段
        # if expected.get("body"):
        #     for field_path, expected_value in expected["body"].items():
        #         if field_path.startswith("@") and field_path.endswith("@"):
        #             # 特殊验证指令
        #             directive = field_path[1:-1]
        #             if directive == "contains":
        #                 assert expected_value in str(response_json), \
        #                     f"响应中未找到预期内容: {expected_value}"
        #         else:
        #             # 普通字段验证
        #             actual_value = _get_nested_value(response_json, field_path)
        #             assert actual_value == expected_value, \
        #                 f"字段 {field_path} 不匹配，期望 {expected_value}，实际 {actual_value}"
