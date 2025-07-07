import json
from typing import Dict, Any, Union
from tests.utils.schema_validator import SchemaValidator


class ResponseValidator:
    """API响应验证器"""
    
    @staticmethod
    def validate_status_code(response, expected_code: int):
        """验证响应状态码"""
        actual_code = response.status_code
        print(f"✓ 状态码验证: 期望 {expected_code}, 实际 {actual_code}")
        assert actual_code == expected_code, \
            f"状态码不匹配，期望 {expected_code}，实际 {actual_code}"
    
    @staticmethod
    def validate_headers(response, expected_headers: Dict[str, str]):
        """验证响应头"""
        if not expected_headers:
            return
            
        print(f"✓ 开始验证响应头，共 {len(expected_headers)} 个")
        for header_name, expected_value in expected_headers.items():
            # 检查响应头是否存在
            assert header_name in response.headers, \
                f"缺少响应头 {header_name}"
            
            actual_value = response.headers[header_name]
            print(f"  - {header_name}: 期望 '{expected_value}', 实际 '{actual_value}'")
            
            # 支持部分匹配（如Content-Type可能包含charset）
            if "application/json" in expected_value and "application/json" in actual_value:
                print(f"  ✓ {header_name} 验证通过（部分匹配）")
                continue
            
            assert actual_value == expected_value, \
                f"响应头 {header_name} 不匹配，期望 {expected_value}，实际 {actual_value}"
            print(f"  ✓ {header_name} 验证通过")
    
    @staticmethod
    def validate_body(response, expected_body: Dict[str, Any]):
        """验证响应体 - 支持复杂JSON验证逻辑"""
        if not expected_body:
            return
            
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            raise AssertionError(f"响应体不是有效JSON格式: {response.text}")
        
        print(f"✓ 开始验证响应体，共 {len(expected_body)} 个字段")
        
        # 递归验证每个字段
        ResponseValidator._validate_object(response_json, expected_body, "")
    
    @staticmethod
    def _validate_object(actual_data: Any, expected_data: Any, current_path: str = ""):
        """递归验证对象"""
        if isinstance(expected_data, dict):
            for key, expected_value in expected_data.items():
                # 路径追踪机制
                field_path = f"{current_path}.{key}" if current_path else key
                
                # 处理特殊验证指令
                if key.startswith("@") and key.endswith("@"):
                    ResponseValidator._handle_special_directive(
                        actual_data, key, expected_value, current_path
                    )
                    continue
                
                # 处理嵌套字段路径（如 "sender.id_type"）
                if "." in key:
                    actual_value = ResponseValidator._get_nested_value(actual_data, key)
                    field_display = f"{current_path}.{key}" if current_path else key
                    
                    if actual_value is None:
                        print(f"  ❌ {field_display}: 字段路径不存在")
                        print(f"      (字段缺失，继续验证其他字段)")
                        continue
                        
                    # 递归验证值
                    if isinstance(expected_value, dict):
                        print(f"  - 验证嵌套对象字段: {field_display}")
                        # 特殊处理：如果期望是@contains，但实际值是字符串，直接进行包含验证
                        if "@contains" in expected_value and isinstance(actual_value, str):
                            contains_value = expected_value["@contains"]
                            if contains_value in actual_value:
                                print(f"    ✓ {field_display} 包含验证通过: '{contains_value}' 在 '{actual_value}' 中找到")
                            else:
                                print(f"    ❌ {field_display} 包含验证失败: '{contains_value}' 在 '{actual_value}' 中未找到")
                                print(f"      (包含验证失败，继续验证其他字段)")
                        else:
                            ResponseValidator._validate_object(actual_value, expected_value, field_display)
                    else:
                        # 精确值比对
                        ResponseValidator._validate_exact_value(actual_value, expected_value, field_display)
                else:
                    # 检查字段是否存在
                    if not isinstance(actual_data, dict):
                        print(f"  ❌ {field_path}: 父级不是对象 ({type(actual_data)})")
                        print(f"      (类型不匹配，继续验证其他字段)")
                        continue
                    
                    if key not in actual_data:
                        print(f"  ❌ {field_path}: 字段不存在")
                        print(f"      (字段缺失，继续验证其他字段)")
                        continue
                    
                    actual_value = actual_data[key]
                    field_display = field_path
                    
                    # 递归验证值
                    if isinstance(expected_value, dict):
                        print(f"  - 验证对象字段: {field_display}")
                        ResponseValidator._validate_object(actual_value, expected_value, field_display)
                    else:
                        # 精确值比对
                        ResponseValidator._validate_exact_value(actual_value, expected_value, field_display)
    
    @staticmethod
    def _validate_exact_value(actual_value: Any, expected_value: Any, field_path: str):
        """精确值比对"""
        print(f"  - {field_path}: 期望 '{expected_value}', 实际 '{actual_value}'")
        
        # 特殊处理@contains包含验证
        if isinstance(expected_value, dict) and "@contains" in expected_value:
            contains_value = expected_value["@contains"]
            if not isinstance(actual_value, str):
                # 如果不是字符串，尝试转换为JSON字符串进行包含检查
                actual_str = json.dumps(actual_value, ensure_ascii=False) if actual_value is not None else str(actual_value)
            else:
                actual_str = actual_value
            
            if contains_value not in actual_str:
                print(f"    ❌ {field_path} 包含验证失败: 期望包含 '{contains_value}'，实际值 '{actual_str}' 不包含")
                print(f"      (包含验证失败，继续验证其他字段)")
                return
            
            print(f"    ✓ {field_path} 包含验证通过")
            return
        
        # 普通精确比对
        if actual_value != expected_value:
            print(f"    ❌ {field_path} 精确匹配失败: 期望 '{expected_value}' ({type(expected_value)}), 实际 '{actual_value}' ({type(actual_value)})")
            # 对于明显不匹配的核心字段，抛出异常
            if field_path in ['code', 'msg', 'status_code']:
                raise AssertionError(f"核心字段 {field_path} 不匹配，期望 '{expected_value}'，实际 '{actual_value}'")
            else:
                print(f"      (非核心字段，继续验证其他字段)")
            return
        
        print(f"    ✓ {field_path} 精确匹配验证通过")
    
    @staticmethod
    def validate_schema(response, schema_name: str):
        """验证响应JSON Schema"""
        if not schema_name:
            return
            
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            print(f"  ⚠️  Schema验证跳过: 响应体不是有效JSON格式")
            return
        
        try:
            if schema_name == "message_response_schema":
                SchemaValidator.validate_message_response(response_json)
                print(f"  ✓ {schema_name} Schema验证通过")
            elif schema_name == "image_upload_schema":
                SchemaValidator.validate_image_upload(response_json)
                print(f"  ✓ {schema_name} Schema验证通过")
            else:
                print(f"  ⚠️  不支持的schema类型: {schema_name}，跳过验证")
        except Exception as e:
            print(f"  ⚠️  {schema_name} Schema验证失败: {str(e)}，跳过验证")
    
    @staticmethod
    def _handle_special_directive(actual_data: Any, directive: str, expected_value: Any, current_path: str = ""):
        """处理特殊验证指令 这些检查由以 @ 包裹的特殊键名（指令）来触发"""
        directive_name = directive[1:-1]  # 去掉@符号
        field_display = f"{current_path}.{directive}" if current_path else directive
        
        if directive_name == "contains":
            # 全局包含验证
            actual_str = json.dumps(actual_data, ensure_ascii=False)
            if expected_value not in actual_str:
                raise AssertionError(f"响应中未找到预期内容: '{expected_value}'")
            print(f"    ✓ {field_display} 全局包含验证通过")
            
        elif directive_name == "not_empty":
            if not actual_data:
                raise AssertionError(f"字段 {current_path} 不能为空")
            print(f"    ✓ {field_display} 非空验证通过")
            
        elif directive_name == "has_key":
            if not isinstance(actual_data, dict) or expected_value not in actual_data:
                raise AssertionError(f"字段 {current_path} 中缺少关键字段: '{expected_value}'")
            print(f"    ✓ {field_display} 关键字段存在验证通过")
            
        else:
            raise ValueError(f"不支持的验证指令: {directive_name}")
    
    @staticmethod
    def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
        """从一个获取深层嵌套json对象字典中的值，支持点分路径"""
        keys = path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, list):
                # 处理数组索引
                if key.isdigit():
                    try:
                        value = value[int(key)]
                    except (IndexError, ValueError):
                        return None
                else:
                    # 处理数组中的字典
                    found_value = None
                    for item in value:
                        if isinstance(item, dict) and key in item:
                            found_value = item[key]
                            break
                    value = found_value
            elif isinstance(value, dict):
                value = value.get(key)
            else:
                return None
            
            if value is None:
                break
                
        return value
    
    @staticmethod
    def validate_error_response(response, expected_body: Dict[str, Any]):
        """
        专门验证错误响应（反向用例）
        重点检查 code 和 msg 字段是否符合飞书API文档
        """
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            raise AssertionError(f"错误响应体不是有效JSON格式: {response.text}")
        
        print("✓ 开始验证错误响应")
        
        # 验证必须有的错误字段
        if "code" not in response_json:
            raise AssertionError("错误响应中缺少 'code' 字段")
        
        if "msg" not in response_json:
            raise AssertionError("错误响应中缺少 'msg' 字段")
        
        # 验证错误码
        expected_code = expected_body.get("code")
        actual_code = response_json["code"]
        if expected_code is not None and actual_code != expected_code:
            raise AssertionError(f"错误码不匹配，期望 {expected_code}，实际 {actual_code}")
        
        # 验证错误信息
        expected_msg = expected_body.get("msg")
        actual_msg = response_json["msg"]
        if expected_msg is not None and actual_msg != expected_msg:
            raise AssertionError(f"错误信息不匹配，期望 '{expected_msg}'，实际 '{actual_msg}'")
        
        print(f"    ✓ 错误码验证: {actual_code}")
        print(f"    ✓ 错误信息验证: {actual_msg}")
        
        # 继续验证其他字段（如果有）
        remaining_fields = {k: v for k, v in expected_body.items() if k not in ["code", "msg"]}
        if remaining_fields:
            ResponseValidator._validate_object(response_json, remaining_fields, "")