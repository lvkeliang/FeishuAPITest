import json
import logging
from typing import Dict, Any, Literal
from jsonschema import validate, ValidationError
from pydantic import BaseModel, Field, field_validator

# 配置日志
logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """自定义schema验证异常"""
    pass


class SenderModel(BaseModel):
    """发送者信息模型"""
    id: str = Field(..., description="发送者ID")
    id_type: Literal["app_id", "user_id", "email"] = Field(..., description="ID类型")
    sender_type: Literal["app", "user"] = Field(..., description="发送者类型")
    tenant_key: str = Field(..., description="租户KEY")


class MessageBodyModel(BaseModel):
    """消息内容模型"""
    content: str = Field(..., description="序列化的JSON字符串")

    @field_validator('content')
    def content_must_be_valid_json(cls, v):
        try:
            json.loads(v)
        except json.JSONDecodeError:
            raise ValueError('content必须是有效的JSON字符串')
        return v


class MessageDataModel(BaseModel):
    """消息数据模型"""
    body: MessageBodyModel = Field(..., description="消息体")
    chat_id: str = Field(..., description="会话ID")
    create_time: str = Field(..., description="创建时间戳(毫秒)")
    deleted: bool = Field(..., description="是否已删除")
    message_id: str = Field(..., description="消息ID")
    msg_type: Literal["text", "post", "image", "file", "audio", "media", "sticker", "interactive"] = Field(
        ..., description="消息类型"
    )
    sender: SenderModel = Field(..., description="发送者信息")
    update_time: str = Field(..., description="更新时间戳(毫秒)")
    updated: bool = Field(..., description="是否已更新")

    @field_validator('create_time', 'update_time')
    def timestamp_must_be_valid(cls, v):
        if len(v) != 13 or not v.isdigit():
            raise ValueError('时间戳必须是13位毫秒时间戳')
        return v


class BaseResponseModel(BaseModel):
    """基础响应模型"""
    code: int = Field(..., description="错误码")
    msg: str = Field(..., description="错误信息")

    @field_validator('code')
    def code_must_be_zero(cls, v):
        if v != 0:
            raise ValueError(f'业务code应为0, 实际为 {v}')
        return v


class MessageResponseModel(BaseResponseModel):
    """消息API响应模型"""
    data: MessageDataModel = Field(..., description="消息数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 0,
                "msg": "success",
                "data": {
                    "body": {
                        "content": "{\"text\":\"test content\"}"
                    },
                    "chat_id": "oc_af1b63d9a0617a6becd6da0a9ea52c38",
                    "create_time": "1751039631504",
                    "deleted": False,
                    "message_id": "om_x100b4adfa63870bc0ecbe6e94b003fc",
                    "msg_type": "text",
                    "sender": {
                        "id": "cli_a8d4099050b81013",
                        "id_type": "app_id",
                        "sender_type": "app",
                        "tenant_key": "1b5b78543140175e"
                    },
                    "update_time": "1751039631504",
                    "updated": False
                }
            }
        }


# JSON Schema定义
MESSAGE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "number", "const": 0},
        "msg": {"type": "string", "const": "success"},
        "data": {
            "type": "object",
            "properties": {
                "body": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"}
                    },
                    "required": ["content"]
                },
                "chat_id": {"type": "string"},
                "create_time": {"type": "string", "pattern": "^\\d{13}$"},
                "deleted": {"type": "boolean"},
                "message_id": {"type": "string"},
                "msg_type": {
                    "type": "string",
                    "enum": ["text", "post", "image", "file", "audio", "media", "sticker", "interactive"]
                },
                "sender": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "id_type": {"type": "string", "enum": ["app_id", "user_id", "email"]},
                        "sender_type": {"type": "string", "enum": ["app", "user"]},
                        "tenant_key": {"type": "string"}
                    },
                    "required": ["id", "id_type", "sender_type", "tenant_key"]
                },
                "update_time": {"type": "string", "pattern": "^\\d{13}$"},
                "updated": {"type": "boolean"}
            },
            "required": [
                "body", "chat_id", "create_time", "deleted",
                "message_id", "msg_type", "sender", "update_time", "updated"
            ]
        }
    },
    "required": ["code", "msg", "data"]
}


def validate_schema(response_data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    验证响应数据是否符合指定的JSON Schema

    参数:
        response_data: 要验证的响应数据(dict)
        schema: JSON Schema定义(dict)

    返回:
        bool: 验证是否通过

    异常:
        SchemaValidationError: 当验证失败时抛出
    """
    try:
        validate(instance=response_data, schema=schema)

        # 额外业务规则验证
        if "data" in response_data:
            data = response_data["data"]
            if data["create_time"] != data["update_time"]:
                raise ValidationError("新消息的create_time和update_time应该相同")

        return True
    except ValidationError as e:
        error_msg = f"Schema验证失败: {e.message}\n路径: {e.json_path}\n响应数据: {json.dumps(response_data, indent=2)}"
        logger.error(error_msg)
        raise SchemaValidationError(error_msg) from e
    except Exception as e:
        error_msg = f"Schema验证发生意外错误: {str(e)}"
        logger.error(error_msg)
        raise SchemaValidationError(error_msg) from e


def validate_with_model(response_data: Dict[str, Any], model: BaseModel) -> bool:
    """
    使用Pydantic模型验证响应数据

    参数:
        response_data: 要验证的响应数据(dict)
        model: Pydantic模型类

    返回:
        bool: 验证是否通过

    异常:
        SchemaValidationError: 当验证失败时抛出
    """
    try:
        model.parse_obj(response_data)
        return True
    except Exception as e:
        error_msg = f"模型验证失败: {str(e)}\n响应数据: {json.dumps(response_data, indent=2)}"
        logger.error(error_msg)
        raise SchemaValidationError(error_msg) from e