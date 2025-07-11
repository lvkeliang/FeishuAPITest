import csv
import json
import requests
import os
from pathlib import Path
import time
import re

"""
cd tests/test_data/testdata_generator
python testdata_generate.py
"""
# 设置参数
CSV_PATH = "test_params.csv"  # API参数CSV文件路径
OUTPUT_PATH = "generated_test_data.csv"  # 输出CSV文件路径
START_ROW = 5  # 起始行号（包含）
END_ROW = 20  # 结束行号（包含）

# LLM API配置
DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
API_KEY = "9232867e-1626-4516-9e3d-443d567d6673"
MODEL = "doubao-1-5-lite-32k-250115"

# prompt
PROMPT_TEMPLATE = """
你是一个专业的API测试工程师，需要为飞书API的{api_name}接口生成测试数据。
请使用条件组合、边界值分析和错误注入等方法，生成包含pass(正常数据)和xfail(预期失败)的测试用例。

### API参数说明:
{parameters_info}

### 生成要求:
1. 为每个参数生成多种测试数据，包括有效值和无效值
2. 对于无法生成正确的测试用例，例如file_key，open_id等真实数据，生成无效值或空值即可
3. 对于含有多个参数的API，可以对所有参数生成测试数据，并打包为一个content(把参数平铺，不要有上下级结构)，并在description字段说明在哪个参数上设置了无效值
3. 使用以下方法生成测试数据:
   - 条件组合: 组合不同参数的边界值
   - 边界值分析: 针对数值和长度参数
   - 错误注入: 故意插入错误数据，必填的参数可设置空值
   - 等价类划分: 将输入划分为有效和无效等价类
4. 为每个测试用例添加category标签: pass或xfail
5. 为每个测试用例添加method标签: 使用的生成方法
6. 为每个测试用例添加description: 简要描述测试目的

### 输出格式:
以JSON格式返回测试数据，结构如下:
{{
  "test_cases": [
    {{
      "category": "pass",
      "method": "边界值",
      "description": "描述文本",
      "parameters": {{
        "param1": "value1",
        "param2": "value2"
      }}
    }},
    {{
      "category": "xfail",
      "method": "错误注入",
      "description": "描述文本",
      "parameters": {{
        "param1": "value1",
        "param2": "value2"
      }}
    }}
  ]
}}
"""


def read_api_parameters_by_range(csv_path, start_row, end_row):
    """
    从CSV文件中读取指定行范围的API参数，按API名称分组
    """
    apis = {}
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            # 行号从1开始计数，i从0开始
            if i + 1 >= start_row and i + 1 <= end_row:
                api_name = row['api_name']
                if api_name not in apis:
                    apis[api_name] = []
                apis[api_name].append(row)
    return apis


def build_prompt(api_name, parameters):
    """
    构建提示信息
    """
    # 构建参数信息字符串
    parameters_info = "\n".join(
        [
            f"- {p['parameter_name']} ({p['type']}, {'必填' if p['required'] == '是' else '可选'}): {p['description']}\n  测试数据生成指导: {p['test_data_generation_guidance']}"
            for p in parameters]
    )

    # 填充提示模板
    return PROMPT_TEMPLATE.format(
        api_name=api_name,
        parameters_info=parameters_info
    )


def call_doubao_api(prompt):
    """
    调用豆包API生成测试数据
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        print("调用豆包API生成测试数据...")
        response = requests.post(DOUBAO_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API调用失败: {e}")
        return None


def save_test_data_to_csv(test_cases, output_path, api_name):
    """
    将测试数据保存到CSV文件
    """
    # 确保输出目录存在
    output_dir = Path(output_path).parent
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    # 创建CSV文件头
    fieldnames = ["api_name", "category", "method", "description", "content"]

    # 检查文件是否存在, 决定是否写入表头
    file_exists = Path(output_path).exists()

    with open(output_path, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for case in test_cases:
            # 将参数打包为JSON字符串
            content = json.dumps(case["parameters"], ensure_ascii=False)

            row = {
                "api_name": api_name,
                "category": case["category"],
                "method": case["method"],
                "description": case["description"],
                "content": content
            }
            writer.writerow(row)

    print(f"已为 {api_name} 生成 {len(test_cases)} 条测试数据")


def extract_json_from_response(content):
    """
    从API响应中提取JSON内容，处理可能的格式问题
    """
    # 尝试直接解析整个内容
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 如果直接解析失败，尝试提取JSON部分
    try:
        # 查找可能的JSON部分
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON提取失败: {e}")

    return None


def generate_test_data_for_api(api_name, parameters, output_path):
    """
    为单个API生成测试数据
    """
    print(f"\n{'=' * 50}")
    print(f"开始为API '{api_name}' 生成测试数据...")
    print(f"读取到 {len(parameters)} 个参数:")
    for param in parameters:
        print(f"  - {param['parameter_name']}: {param['description']}")

    # 构建提示
    prompt = build_prompt(api_name, parameters)
    print("\n生成的提示:\n", prompt[:500] + "..." if len(prompt) > 500 else prompt)

    # 调用LLM API
    response = call_doubao_api(prompt)

    if not response or "choices" not in response or not response["choices"]:
        print(f"未获取到 {api_name} 的有效测试数据")
        return

    # 解析响应
    try:
        content = response["choices"][0]["message"]["content"]
        print("\nAPI响应内容:")
        print(content[:500] + "..." if len(content) > 500 else content)

        # JSON提取
        test_data = extract_json_from_response(content)
        if not test_data:
            print(f"无法从响应中提取有效的JSON数据: {api_name}")
            return

        test_cases = test_data.get("test_cases", [])

        if not test_cases:
            print(f"未为 {api_name} 生成测试用例")
            return

        # 保存到CSV
        save_test_data_to_csv(test_cases, output_path, api_name)
    except (KeyError, TypeError) as e:
        print(f"解析响应数据失败: {e}")


def main():
    """
    主函数：生成指定行范围的测试数据
    """
    print("=" * 50)
    print("飞书API测试数据生成器")
    print(f"行范围: {START_ROW} - {END_ROW}")
    print("=" * 50)

    # 1. 读取指定行范围的API参数
    apis = read_api_parameters_by_range(CSV_PATH, START_ROW, END_ROW)
    if not apis:
        print(f"在行 {START_ROW}-{END_ROW} 范围内未找到API参数")
        return

    print(f"找到 {len(apis)} 个API:")
    for api_name in apis:
        print(f"  - {api_name} ({len(apis[api_name])}个参数)")

    # 2. 为每个API生成测试数据
    for api_name, parameters in apis.items():
        generate_test_data_for_api(api_name, parameters, OUTPUT_PATH)
        # 添加延迟避免API限流
        time.sleep(2)

    print("\n" + "=" * 50)
    print(f"所有API的测试数据已保存到: {OUTPUT_PATH}")
    print("=" * 50)


if __name__ == "__main__":
    main()