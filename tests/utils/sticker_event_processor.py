# -*- coding: UTF-8 -*-
"""
    挂起接收消息订阅并监测表情包的脚本
"""

import csv
import json
import os
from pathlib import Path
from typing import Set, Dict
import lark_oapi as lark

# 配置文件路径
CSV_FILE_PATH = "../test_data/other/sticker_message.csv"
FIELD_NAMES = [
    "event_id", "create_time", "tenant_key", "app_id",
    "message_id", "chat_id", "chat_type", "message_type", "file_key",
    "sender_id", "sender_type", "sender_open_id", "sender_union_id"
]

# 内存缓存已处理的file_key
processed_file_keys: Set[str] = set()


def load_existing_file_keys():
    """加载已存在的file_key到内存缓存"""
    if not Path(CSV_FILE_PATH).exists():
        return

    try:
        with open(CSV_FILE_PATH, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if 'file_key' in reader.fieldnames:
                for row in reader:
                    if row['file_key']:
                        processed_file_keys.add(row['file_key'])
    except Exception as e:
        print(f"加载现有file_key失败: {e}")


def save_sticker_message(data: Dict):
    """保存贴纸消息到CSV文件"""
    try:
        # 确保目录存在
        output_dir = Path(CSV_FILE_PATH).parent
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        # 提取关键数据
        header = data["header"]
        event = data["event"]
        message = event["message"]
        sender = event["sender"]

        # 解析content字段
        content = json.loads(message["content"])
        file_key = content.get("file_key", "")

        # 检查是否已存在
        if file_key and file_key in processed_file_keys:
            print(f"跳过已存在的file_key: {file_key}")
            return False

        # 准备行数据
        row = {
            "event_id": header["event_id"],
            "create_time": header["create_time"],
            "tenant_key": header["tenant_key"],
            "app_id": header["app_id"],
            "message_id": message["message_id"],
            "chat_id": message["chat_id"],
            "chat_type": message["chat_type"],
            "message_type": message["message_type"],
            "file_key": file_key,
            "sender_id": sender["sender_id"].get("user_id", ""),
            "sender_type": sender["sender_type"],
            "sender_open_id": sender["sender_id"].get("open_id", ""),
            "sender_union_id": sender["sender_id"].get("union_id", "")
        }

        # 写入CSV
        file_exists = Path(CSV_FILE_PATH).exists()
        with open(CSV_FILE_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELD_NAMES)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        # 更新缓存
        if file_key:
            processed_file_keys.add(file_key)

        print(f"成功保存sticker消息: {file_key}")
        return True

    except json.JSONDecodeError:
        print("content字段JSON解析失败")
    except KeyError as e:
        print(f"缺少必要字段: {e}")
    except Exception as e:
        print(f"保存消息失败: {e}")

    return False


def do_p2_im_message_receive_v1(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """处理消息接收事件"""
    try:
        # 转换为字典格式
        data_dict = json.loads(lark.JSON.marshal(data))

        # 检查是否为贴纸消息
        if data_dict["event"]["message"]["message_type"] == "sticker":
            save_sticker_message(data_dict)

    except Exception as e:
        print(f"处理消息事件失败: {e}")


def main():
    """主函数"""
    # 加载现有file_key
    load_existing_file_keys()
    print(f"已加载 {len(processed_file_keys)} 个file_key到缓存")

    # 注册事件处理器
    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1) \
        .build()

    # 创建客户端
    cli = lark.ws.Client(
        "cli_a8e744bced3c5013",
        "2T1tCaupIwIZ5Zdq5UqUnhuG4FIDGOMq",
        event_handler=event_handler,
        log_level=lark.LogLevel.DEBUG
    )

    # 启动长连接
    print("开始监听sticker消息事件...")
    cli.start()


if __name__ == "__main__":
    main()