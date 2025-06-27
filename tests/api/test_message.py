import pytest
import json
import allure
from ..utils.client import FeishuClient
from ..utils.config_loader import config
from tests.utils.schema_validator import (
    validate_schema,
    validate_with_model,
    MessageResponseModel,
    MESSAGE_RESPONSE_SCHEMA
)
from ..utils.file_uploader import FileUploader
from ..utils.message_builder import MessageBuilder


@pytest.fixture(scope="module")
def feishu_client():
    """共享的Feishu客户端fixture"""
    return FeishuClient()


@pytest.fixture
def test_user():
    """获取测试用户fixture"""
    return config.get_test_account("吕科良")


@pytest.fixture
def message_test_data(test_user, request):
    """参数化的消息测试数据fixture"""
    msg_type = request.param if hasattr(request, 'param') else 'text'
    return {
        "receive_id": test_user["open_id"],
        "msg_type": msg_type,
        "content": {"text": f"测试{msg_type}类型消息"}
    }


# 测试发送文本消息（详细验证）
# def test_send_text_message(feishu_client, test_user):
#     """测试发送文本消息（完整验证）"""
#     # 准备测试数据
#     test_content = "自动化测试消息"
#     test_data = {
#         "receive_id": test_user["open_id"],
#         "msg_type": "text",
#         "content": json.dumps({"text": test_content})
#     }
#
#     # 发送请求
#     response = feishu_client.send_message(
#         method="POST",
#         endpoint="/open-apis/im/v1/messages",
#         params={"receive_id_type": "open_id"},
#         json=test_data
#     )
#
#     if response.status_code != 200:
#         print(f"请求失败: {response.status_code}")
#         print("响应内容:", response.json())  # 打印错误详情
#
#     # 验证基础响应
#     assert response.status_code == 200
#     response_data = response.json()
#
#     # 验证业务码和消息
#     assert response_data["code"] == 0
#     assert response_data["msg"] == "success"
#
#     # 验证完整响应结构
#     validate_schema(response_data, MESSAGE_RESPONSE_SCHEMA)
#
#     # 使用Pydantic模型验证
#     validate_with_model(response_data, MessageResponseModel)
#
#     # 验证业务逻辑
#     data = response_data["data"]
#     assert len(data["message_id"]) > 0
#     assert data["msg_type"] == "text"
#     assert not data["deleted"]
#     assert not data["updated"]
#     assert data["sender"]["sender_type"] == "app"
#     assert data["sender"]["id_type"] == "app_id"
#
#     # 验证时间戳
#     assert len(data["create_time"]) == 13
#     assert len(data["update_time"]) == 13
#     assert data["create_time"] == data["update_time"]
#
#     # 验证消息内容
#     content = json.loads(data["body"]["content"])
#     assert content["text"] == test_content


@pytest.fixture(scope="module")
def uploader(feishu_client):
    return FileUploader(feishu_client)


# 参数化测试所有消息类型
@pytest.mark.parametrize("msg_type,content_generator", [
    ("text", lambda u: MessageBuilder.build_text()),
    ("post", lambda u: MessageBuilder.build_post()),
    ("image", lambda u: MessageBuilder.build_image(u)),
    ("interactive", lambda u: MessageBuilder.build_interactive()),
    # 可扩展其他消息类型
])
def test_all_message_types(feishu_client, test_user, uploader, msg_type, content_generator):
    """参数化测试所有消息类型"""
    # 生成消息内容
    with allure.step("Step 1: 生成消息内容"):
        content = content_generator(uploader)

    with allure.step("Step 2: 发送请求"):
        response = feishu_client.send_message(
            method="POST",
            endpoint="/open-apis/im/v1/messages",
            params={"receive_id_type": "open_id"},
            json={
                "receive_id": test_user["open_id"],
                "msg_type": msg_type,
                "content": content
            }
        )

    with allure.step("Step 3: 验证响应"):
        assert response.status_code == 200, f"请求失败: {response.json().get('msg')}"
        response_data = response.json()
        assert response_data["code"] == 0, f"请求失败: {response.json().get('msg')}"
        assert response_data["data"]["msg_type"] == msg_type, f"请求失败: {response.json().get('msg')}"
        allure.dynamic.title(f"测试通过 - 返回消息: {response_data.get('msg')}")
