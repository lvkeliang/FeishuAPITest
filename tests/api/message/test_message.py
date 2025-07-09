import allure
import pytest
from typing import Dict, Any
from tests.client.client import feishu_client
from tests.test_data.case_loader import test_case_loader
from tests.utils.config_loader import config
from tests.utils.response_validator import ResponseValidator


# 装饰器标识msg_type
def case_msg_type(msg_type):
    def decorator(func):
        func._msg_type = msg_type  # 附加属性
        return func

    return decorator


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
# @pytest.mark.skip(reason="正在开发其他的测试")
@case_msg_type("text")
def test_text_messages(client, prepared_test_case, receiver_info):
    _generic_message_test(feishu_client, prepared_test_case, receiver_info)


# @pytest.mark.skip(reason="正在开发其他的测试")
@case_msg_type("image")
def test_image_messages(client, prepared_test_case, receiver_info):
    _generic_message_test(feishu_client, prepared_test_case, receiver_info)


# @pytest.mark.skip(reason="正在开发其他的测试")
@case_msg_type("post")
def test_post_messages(client, prepared_test_case, receiver_info):
    _generic_message_test(feishu_client, prepared_test_case, receiver_info)


# @pytest.mark.skip(reason="正在开发其他的测试")
@case_msg_type("interactive")
def test_interactive_messages(client, prepared_test_case, receiver_info):
    _generic_message_test(feishu_client, prepared_test_case, receiver_info)


# @pytest.mark.skip(reason="正在开发其他的测试")
@case_msg_type("file")
def test_file_messages(client, prepared_test_case, receiver_info):
    _generic_message_test(feishu_client, prepared_test_case, receiver_info)


# @pytest.mark.skip(reason="正在开发其他的测试")
@case_msg_type("audio")
def test_audio_messages(client, prepared_test_case, receiver_info):
    _generic_message_test(feishu_client, prepared_test_case, receiver_info)


# @pytest.mark.skip(reason="正在开发其他的测试")
@case_msg_type("media")
def test_media_messages(client, prepared_test_case, receiver_info):
    _generic_message_test(feishu_client, prepared_test_case, receiver_info)


def _generic_message_test(client, prepared_test_case, receiver_info):
    receive_id_type, receive_id = receiver_info
    """通用消息发送测试"""
    with allure.step("Step 1: 准备测试用例"):
        test_data = prepared_test_case
        request_data = test_data["request"]

        # --- 动态注入参数 ---
        # 1. 注入 receive_id_type 到查询参数
        query_params = request_data.get("query_params", {})
        query_params["receive_id_type"] = receive_id_type  # 覆盖或新增

        # 2. 注入 receive_id 到请求体
        request_body = request_data.get("body", {})
        if test_data["original_case"].category == "positive":
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
        ResponseValidator.validate_status_code(response, expected["status_code"])

        # 2. 验证响应头
        if expected.get("headers"):
            ResponseValidator.validate_headers(response, expected["headers"])

        # 3. 验证响应体Schema
        if expected.get("schema"):
            ResponseValidator.validate_schema(response, expected["schema"])

        # 4. 验证响应体具体字段
        if expected.get("body"):
            # 判断是否为错误响应（反向用例）
            if test_data["original_case"].category == "negative" or response.status_code >= 400:
                ResponseValidator.validate_error_response(response, expected["body"])
            else:
                ResponseValidator.validate_body(response, expected["body"])
