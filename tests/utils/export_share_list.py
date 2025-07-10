# -*- coding: UTF-8 -*-
"""
    批量获取chat_id与用户open_id的脚本
"""

import csv
import os
import json
import requests
from pathlib import Path
import yaml
from typing import List, Dict, Set

chat_output_csv = "../test_data/other/chat_list.csv"
user_input_csv = "../test_data/other/share_user_data.csv"
user_output_csv = "../test_data/other/user_list.csv"

def get_tenant_access_token(app_id, app_secret):
    """获取租户访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取token失败: {data.get('msg')}")
    return data["tenant_access_token"]

def config_loader():
    # 读取配置文件
    config_dir = Path(__file__).parent.parent.parent / "config"

    # 加载配置
    with open(config_dir / "test_env" / "dev.yaml", encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 获取飞书应用凭证
    feishu_config = config.get('feishu', {})
    app_id = feishu_config.get('app_id')
    app_secret = feishu_config.get('app_secret')
    return app_id, app_secret


def get_chat_list(access_token, page_size=100):
    """获取群列表"""
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    params = {
        "page_size": page_size
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取群列表失败: {data.get('msg')}")
    return data["data"]["items"]


def export_chat_list_to_csv(output_path="reports/chat_list.csv"):
    """获取机器人所在的群列表并导出为CSV文件"""
    # 读取配置文件
    app_id, app_secret = config_loader()
    try:
        # 1. 获取应用凭证
        app_id = os.getenv("FEISHU_APP_ID", app_id)
        app_secret = os.getenv("FEISHU_APP_SECRET", app_secret)

        # 2. 获取访问令牌
        access_token = get_tenant_access_token(app_id, app_secret)

        # 3. 获取群列表
        chat_list = get_chat_list(access_token)

        # 4. 提取所需数据
        chat_data = []
        for chat in chat_list:
            chat_data.append({
                "name": chat.get("name", "未知群组"),
                "chat_id": chat.get("chat_id", "")
            })

        # 5. 确保输出目录存在
        output_dir = Path(output_path).parent
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        # 6. 写入CSV文件
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['name', 'chat_id']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for chat in chat_data:
                writer.writerow(chat)

        print(f"成功导出 {len(chat_data)} 个群组到 {output_path}")
        return True

    except requests.exceptions.RequestException as req_err:
        print(f"网络请求错误: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"JSON解析错误: {json_err}")
    except KeyError as key_err:
        print(f"数据字段缺失: {key_err}")
    except ValueError as val_err:
        print(f"配置错误: {val_err}")
    except RuntimeError as rt_err:
        print(f"API错误: {rt_err}")
    except IOError as io_err:
        print(f"文件操作错误: {io_err}")
    except Exception as e:
        print(f"未处理的异常: {e}")

    return False


def read_user_identifiers(csv_path: str) -> Dict[str, List[str]]:
    """
    从CSV文件中读取用户标识信息（邮箱和手机号）

    参数:
        csv_path: CSV文件路径

    返回:
        包含邮箱列表和手机号列表的字典
    """
    emails = []
    mobiles = []

    try:
        # 尝试使用不同编码打开文件
        encodings = ['utf-8-sig', 'gbk', 'gb18030', 'latin1', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(csv_path, 'r', encoding=encoding) as csvfile:
                    # 使用 Sniffer 检测 CSV 格式
                    dialect = csv.Sniffer().sniff(csvfile.read(1024))
                    csvfile.seek(0)

                    reader = csv.DictReader(csvfile, dialect=dialect)

                    # 标准化列名：去除空格并转为小写
                    normalized_fields = [field.strip().lower() for field in reader.fieldnames]

                    # 检查必要的列是否存在
                    if 'email' not in normalized_fields or 'mobile' not in normalized_fields:
                        raise ValueError("CSV文件必须包含 'email' 和 'mobile' 列（不区分大小写和空格）")

                    # 创建原始列名到标准化列名的映射
                    field_mapping = {field: normalized for field, normalized in
                                     zip(reader.fieldnames, normalized_fields)}

                    for row in reader:
                        # 查找 email 列
                        email_key = next((k for k, v in field_mapping.items() if v == 'email'), None)
                        if email_key and row.get(email_key, '').strip():
                            emails.append(row[email_key].strip())

                        # 查找 mobile 列
                        mobile_key = next((k for k, v in field_mapping.items() if v == 'mobile'), None)
                        if mobile_key and row.get(mobile_key, '').strip():
                            mobiles.append(row[mobile_key].strip())

                # 如果成功读取，跳出循环
                print(f"使用 {encoding} 编码成功读取文件")
                break

            except UnicodeDecodeError:
                # 尝试下一种编码
                continue
            except Exception as e:
                # 其他错误直接抛出
                raise RuntimeError(f"读取CSV文件失败: {str(e)}")
        else:
            # 所有编码尝试都失败
            raise UnicodeDecodeError("无法确定文件编码，请尝试转换文件为UTF-8格式")

        return {'emails': emails, 'mobiles': mobiles}

    except FileNotFoundError:
        raise FileNotFoundError(f"文件未找到: {csv_path}")
    except Exception as e:
        raise RuntimeError(f"读取CSV文件失败: {str(e)}")


def batch_get_user_ids(access_token: str, identifiers: Dict[str, List[str]]) -> Dict[str, str]:
    """
    批量获取用户ID

    参数:
        access_token: 飞书访问令牌
        identifiers: 包含邮箱和手机号的字典

    返回:
        用户标识到open_id的映射字典
    """
    url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # 构建请求体
    payload = {
        "emails": identifiers['emails'],
        "mobiles": identifiers['mobiles'],
        "include_resigned": True
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise RuntimeError(f"API请求失败: {str(e)}")

    if data.get("code") != 0:
        error_msg = data.get("msg", "未知错误")
        raise RuntimeError(f"获取用户ID失败: {error_msg} (code={data.get('code')})")

    # 处理响应数据
    user_mapping = {}
    for user in data.get('data', {}).get('user_list', []):
        # 获取用户ID（响应为user_id字段）
        user_id = user.get('user_id')
        if not user_id:
            continue  # 跳过没有user_id的记录

        # 优先使用邮箱作为标识
        if user.get('email'):
            user_mapping[user['email']] = user_id
        # 其次使用手机号
        elif user.get('mobile'):
            user_mapping[user['mobile']] = user_id

    return user_mapping


def get_existing_open_ids(output_path: str) -> Set[str]:
    """
    获取输出文件中已存在的open_id

    参数:
        output_path: 输出文件路径

    返回:
        已存在的open_id集合
    """
    existing_ids = set()

    # 如果文件不存在，返回空集合
    if not Path(output_path).exists():
        return existing_ids

    try:
        with open(output_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            # 检查是否有open_id列
            if 'open_id' in reader.fieldnames:
                for row in reader:
                    if row['open_id'] and row['open_id'].strip():
                        existing_ids.add(row['open_id'].strip())

    except Exception as e:
        print(f"警告: 读取现有open_id失败 - {str(e)}")

    return existing_ids


def write_new_open_ids(output_path: str, user_mapping: Dict[str, str], existing_ids: Set[str]):
    """
    将新的open_id写入CSV文件

    参数:
        output_path: 输出文件路径
        user_mapping: 用户标识到open_id的映射
        existing_ids: 已存在的open_id集合
    """
    # 确保输出目录存在
    output_dir = Path(output_path).parent
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    # 确定文件是否存在，决定是否写入表头
    file_exists = Path(output_path).exists()

    with open(output_path, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['identifier', 'open_id']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # 如果文件不存在，写入表头
        if not file_exists:
            writer.writeheader()

        # 写入新数据
        new_count = 0
        for identifier, open_id in user_mapping.items():
            # 跳过已存在的open_id
            if open_id in existing_ids:
                continue

            writer.writerow({
                'identifier': identifier,
                'open_id': open_id
            })
            new_count += 1
            # 添加到现有集合，避免重复写入
            existing_ids.add(open_id)

        print(f"成功写入 {new_count} 个新的open_id到 {output_path}")


def batch_fetch_user_ids(input_csv: str, output_csv: str):
    """
    批量获取用户ID主函数

    参数:
        input_csv: 输入CSV文件路径
        output_csv: 输出CSV文件路径
    """
    app_id, app_secret = config_loader()
    try:
        # 1. 获取应用凭证
        app_id = os.getenv("FEISHU_APP_ID", app_id)
        app_secret = os.getenv("FEISHU_APP_SECRET", app_secret)

        # 2. 获取访问令牌
        access_token = get_tenant_access_token(app_id, app_secret)
        print("成功获取访问令牌")

        # 3. 读取用户标识
        identifiers = read_user_identifiers(input_csv)
        print(f"读取到 {len(identifiers['emails'])} 个邮箱和 {len(identifiers['mobiles'])} 个手机号")

        # 4. 批量获取用户ID
        user_mapping = batch_get_user_ids(access_token, identifiers)
        print(f"成功获取 {len(user_mapping)} 个用户ID")

        # 5. 获取已存在的open_id
        existing_ids = get_existing_open_ids(output_csv)
        print(f"找到 {len(existing_ids)} 个已存在的open_id")

        # 6. 写入新的open_id
        write_new_open_ids(output_csv, user_mapping, existing_ids)

        return True

    except Exception as e:
        print(f"错误: {str(e)}")
        return False


if __name__ == "__main__":
    # 主菜单
    print("请选择要执行的功能:")
    print("1. 导出群列表")
    print("2. 批量获取用户ID")

    choice = input("请输入选项 (1 或 2): ").strip()

    if choice == "1":
        # 执行导出
        print(f"将结果写入 {chat_output_csv}...")
        success = export_chat_list_to_csv(chat_output_csv)

        if success:
            print("操作成功完成")
        else:
            print("操作失败，请检查错误信息")

    elif choice == "2":
        print(f"从 {user_input_csv} 读取用户标识...")
        print(f"将结果写入 {user_output_csv}...")

        success = batch_fetch_user_ids(user_input_csv, user_output_csv)

        if success:
            print("操作成功完成")
        else:
            print("操作失败，请检查错误信息")
    else:
        print("无效的选项，请重新运行程序并输入 1 或 2")