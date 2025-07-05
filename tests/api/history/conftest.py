import pytest

from tests.test_data.case_loader import test_case_loader


def extract_msg_type_from_test_name(test_name):
    """从测试函数名中提取消息类型"""
    # 示例：test_text_messages -> "text"
    # 示例：test_image_send -> "image"
    parts = test_name.split('_')
    if len(parts) >= 2 and parts[0] == "test":
        return parts[1]  # 取test后的第一个单词
    return None


def pytest_generate_tests(metafunc):
    if "prepared_test_case" in metafunc.fixturenames:
        # 从测试函数名提取msg_type
        msg_type = extract_msg_type_from_test_name(metafunc.definition.name)

        if not msg_type:
            pytest.skip(f"Cannot determine msg_type from test name: {metafunc.definition.name}")

        test_cases = test_case_loader.load_cases_by_type("history", msg_type)
        metafunc.parametrize(
            "prepared_test_case",
            test_cases,
            indirect=True,
            ids=lambda c: f"{c.category}_{c.name}"
        )