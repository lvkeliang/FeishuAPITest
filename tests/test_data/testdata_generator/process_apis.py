import os
import csv
import re
import requests
from dotenv import load_dotenv
import yaml

"""
根据api_docs下的API文档生成参数总结，以供后续生成参数样例
cd tests/test_data/testdata_generator
python process_apis.py
=====================================================
api_docs内容示例：
api_name：send_message-text # 表示测试send_message接口下特定的text文件格式
请求体：{
.receive_id("your_open_id")
.msg_type("text")
.content("{"text":"test content"}")
}
参数说明：（名称///类型///是否必填///描述）
receive_id///
string///
是///
消息接收者的 ID，ID 类型与查询参数 receive_id_type 的取值一致。
注意事项：
给用户发送消息时，用户需要在机器人的可用范围内。例如，你需要给企业全员发送消息，则需要将应用的可用范围设置为全体员工。
给群组发送消息时，机器人需要在该群组中，且在群组内拥有发言权限。
如果消息接收者为用户，推荐使用用户的 open_id。
示例值："ou_7d8a6e6df7621556ce0d21922b676706ccs"
......
"""

# 加载配置函数
def load_config():
    config_path = "td_env.yaml"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件 {config_path} 不存在")

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# 加载配置
config = load_config()
api_config = config.get('api', {})

# 使用配置
API_KEY = api_config.get('API_KEY')
API_URL = api_config.get('API_URL')
MODEL = api_config.get('model', "Pro/deepseek-ai/DeepSeek-R1")  # 默认值
MAX_TOKENS = api_config.get('MAX_TOKENS', 10000)  # 默认值
MAX_FILE_SIZE = api_config.get('MAX_FILE_SIZE', 20000)  # 默认值

def read_api_doc(file_path):
    """读取API文档文件内容，检查长度"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查文件大小是否超过限制
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(f"文件过大 ({len(content)}字符)，超过最大限制 {MAX_FILE_SIZE}字符")

    return content


def generate_prompt(api_name, api_content):
    """prompt"""
    return f"""
你是一个专业的API测试工程师，请分析以下API文档并提取测试参数，以用于批量生成测试数据。严格按照以下要求返回：
1. 输出CSV格式，每行一个参数
2. 包含表头：api_name,parameter_name,type,required,description,test_data_generation_guidance
3. 参数层级使用点号表示（如content.text）
4. type: 参数的数据类型（如string, object, array等）
5. required: 是否必填（是/否）
6. description: 参数的简要描述（从文档中总结）
7. test_data_generation_guidance: 测试数据生成指导，根据边界值分析、错误注入等方法生成，用双引号包裹，内容为逗号分隔的生成要点（例如：生成：1.普通文本 2.空字符串 3.XSS攻击字符串 4.多语言文本 5.带样式标签文本）
8. 只返回CSV内容，不要包含任何额外文本
9. API名称可能会有细分，表示该API下的细化类型，例如api_name为send_message-post时，文档中出现“api_name为send_message-post-text”，其下参数的api_name要定义为send_message-post-text

API名称：{api_name}
API文档内容：
{api_content}
"""


def call_llm_api(prompt):
    """调用SiliconFlow的Deepseek-ai Pro API"""
    # 调试输出
    # print(f"提示长度: {len(prompt)}字符")

    if len(prompt) > MAX_TOKENS:
        raise ValueError(f"提示过长 ({len(prompt)}字符)，超过最大限制 {MAX_TOKENS}字符")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 4000
    }

    try:
        # 调试输出请求详情
        # print("发送请求到SiliconFlow API...")
        # print(f"请求头: Authorization: Bearer {API_KEY[:5]}...{API_KEY[-5:]}")
        # print(f"模型: {payload['model']}")

        response = requests.post(API_URL, json=payload, headers=headers, timeout=100)

        # 调试输出响应状态
        # print(f"响应状态码: {response.status_code}")
        # if response.status_code == 401:
        #     print("错误: 未经授权 (401 Unauthorized)")
        #     print("可能原因:")
        #     print("1. API密钥无效或过期")
        #     print("2. 账户没有访问权限")
        #     print("3. 模型名称错误")
        #     return None

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"API调用失败: {e}")
        # if hasattr(e, 'response') and e.response is not None:
        #     print(f"错误响应内容: {e.response.text[:500]}")
        return None


def parse_llm_response(response):
    """解析LLM返回的CSV内容"""
    lines = response.split('\n')
    # 跳过表头行
    return [line for line in lines if line and not line.startswith('api_name')]


def save_to_csv(data, output_file="api_test_params.csv"):
    """保存数据到CSV文件，避免重复记录"""
    existing_records = set()
    file_exists = os.path.exists(output_file)

    # 读取现有记录
    if file_exists:
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                header = next(reader)  # 读取表头
                if header != ["api_name", "parameter_name", "type", "required", "description",
                              "test_data_generation_guidance"]:
                    # 表头不匹配，需要重建文件
                    file_exists = False
                    print("警告: CSV表头不匹配，将重建文件")
                else:
                    for row in reader:
                        if len(row) >= 2:
                            existing_records.add((row[0], row[1]))  # (api_name, parameter_name)
            except StopIteration:
                # 空文件
                file_exists = False

    # 确定文件打开模式
    mode = 'w' if not file_exists else 'a'

    with open(output_file, mode, newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # 如果是新文件或需要重建，写入表头
        if mode == 'w':
            writer.writerow(
                ["api_name", "parameter_name", "type", "required", "description", "test_data_generation_guidance"])
            print(f"创建新文件并写入表头: {output_file}")

        new_count = 0
        for line in data:
            try:
                row = next(csv.reader([line]))
                if len(row) < 6:
                    continue

                # 检查是否已存在
                key = (row[0], row[1])
                if key not in existing_records:
                    writer.writerow(row)
                    existing_records.add(key)
                    print(f"新增记录: {row[0]}.{row[1]}")
                    new_count += 1
                else:
                    print(f"跳过重复: {row[0]}.{row[1]}")
            except Exception as e:
                print(f"解析失败: {line} | 错误: {e}")

        return new_count


def process_api_docs(docs_dir="api_docs"):
    """处理目录中的所有API文档"""
    # 创建日志文件
    log_file = "api_processing.log"
    with open(log_file, 'a', encoding='utf-8') as log:
        log.write(f"\n\n===== 开始处理API文档 ({len(os.listdir(docs_dir))}个文件) =====\n")

    processed = 0
    skipped = 0

    for filename in os.listdir(docs_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(docs_dir, filename)
            api_name = os.path.splitext(filename)[0]

            log_msg = f"\n处理API: {api_name}"
            print(log_msg)

            try:
                # 读取API文档
                api_content = read_api_doc(file_path)
                log_msg += f" | 文件大小: {len(api_content)}字符"

                # 生成提示并调用LLM
                prompt = generate_prompt(api_name, api_content)
                log_msg += f" | 提示大小: {len(prompt)}字符"

                response = call_llm_api(prompt)

                if response:
                    log_msg += f" | 响应大小: {len(response)}字符"
                    parsed_data = parse_llm_response(response)

                    if parsed_data:
                        new_count = save_to_csv(parsed_data)
                        log_msg += f" | 新增参数: {new_count}个"
                        processed += 1
                    else:
                        log_msg += " | 警告: 未解析到有效数据"
                else:
                    log_msg += " | 错误: 未获取到LLM响应"
            except ValueError as ve:
                log_msg += f" | 错误: {str(ve)} | 状态: 已跳过"
                skipped += 1
            except Exception as e:
                log_msg += f" | 错误: {str(e)} | 状态: 处理失败"
                skipped += 1

            # 记录日志
            print(log_msg)
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write(log_msg + "\n")

    # 总结报告
    summary = f"\n处理完成: 成功处理 {processed} 个API, 跳过 {skipped} 个文件"
    print(summary)
    with open(log_file, 'a', encoding='utf-8') as log:
        log.write(summary + "\n")


if __name__ == "__main__":
    process_api_docs()