import os
import csv
import re
import requests
from dotenv import load_dotenv

# 加载环境变量（API密钥）
load_dotenv()
API_KEY = os.getenv("sk-chaqlygkvqpovgczihfimcvdmcojkoxwrrclfibehohoioyc")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

# 设置token限制
MAX_TOKENS = 10000  # 根据Deepseek-ai Pro的128K上下文，设置保守阈值
MAX_FILE_SIZE = 20000  # 字符数限制（约等于token数）

"""
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
你是一个专业的API测试工程师，请分析以下API文档并提取测试参数。严格按照以下要求返回：
1. 输出CSV格式，每行一个参数
2. 包含表头：api_name,parameter_name,type,required,description,test_data_generation_guidance
3. 参数层级使用点号表示（如content.text）
4. 测试数据生成指导用双引号包裹，内容为逗号分隔的生成要点
5. 只返回CSV内容，不要包含任何额外文本

API名称：{api_name}
API文档内容：
{api_content}
"""


def call_llm_api(prompt):
    """调用Deepseek API"""
    # 检查提示长度是否超过限制
    if len(prompt) > MAX_TOKENS:
        raise ValueError(f"提示过长 ({len(prompt)}字符)，超过最大限制 {MAX_TOKENS}字符")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "Pro/deepseek-ai/DeepSeek-R1",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 5000
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"API调用失败: {e}")
        return None


def parse_llm_response(response):
    """解析LLM返回的CSV内容"""
    lines = response.split('\n')
    # 跳过表头行
    return [line for line in lines if line and not line.startswith('api_name')]


def save_to_csv(data, output_file="api_test_params.csv"):
    """保存数据到CSV文件，避免重复记录"""
    existing_records = set()

    # 读取现有记录
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # 跳过表头
            for row in reader:
                if len(row) >= 2:
                    existing_records.add((row[0], row[1]))  # (api_name, parameter_name)

    # 追加新记录
    with open(output_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not os.path.exists(output_file):
            writer.writerow(
                ["api_name", "parameter_name", "type", "required", "description", "test_data_generation_guidance"])

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