import json
from pathlib import Path
from jsonschema import validate, ValidationError


class SchemaValidator:
    SCHEMA_DIR = Path(__file__).parent.parent / "schemas"

    @classmethod
    def validate_message_response(cls, response_data: dict):
        """验证消息响应结构"""
        schema_path = cls.SCHEMA_DIR / "message_response.json"
        return cls._validate_with_schema(response_data, schema_path)

    @classmethod
    def validate_image_upload(cls, response_data: dict):
        """验证图片上传响应"""
        schema_path = cls.SCHEMA_DIR / "image_upload.json"
        return cls._validate_with_schema(response_data, schema_path)

    @staticmethod
    def _validate_with_schema(data: dict, schema_path: Path):
        try:
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema文件不存在: {schema_path}")
            
            with open(schema_path, encoding='utf-8') as f:
                schema = json.load(f)
            validate(instance=data, schema=schema)
            return True
        except FileNotFoundError as e:
            raise ValueError(f"Schema文件缺失: {str(e)}") from e
        except ValidationError as e:
            raise ValueError(f"Schema验证失败: {e.message}") from e
        except Exception as e:
            raise ValueError(f"Schema验证出错: {str(e)}") from e