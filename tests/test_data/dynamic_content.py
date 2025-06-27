# tests/test_data/dynamic_content.py
from faker import Faker

def generate_test_card():
    """生成动态测试卡片内容"""
    fake = Faker()
    return {
        "header": {"title": {"content": fake.sentence()}},
        "elements": [{
            "tag": "div",
            "text": {"content": fake.text(), "tag": "plain_text"}
        }]
    }