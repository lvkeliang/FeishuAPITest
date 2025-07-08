import pytest

from tests.test_data.case_loader import test_case_loader
from tests.utils.config_loader import config


def pytest_generate_tests(metafunc):
    if "prepared_test_case" in metafunc.fixturenames:
        # 从测试函数提取msg_type
        test_type = getattr(metafunc.function, "_test_type", None)

        if not test_type:
            pytest.skip(f"Cannot determine msg_type from test name: {metafunc.definition.name}")

        test_cases = test_case_loader.load_cases_by_type("history", test_type)
        metafunc.parametrize(
            "prepared_test_case",
            test_cases,
            indirect=True,
            ids=lambda c: f"{c.category}_{c.name}"
        )


@pytest.fixture(params=[
    ("chat", config.get_test_account(0)["chat_id"]),
    ("chat", config.get_test_group(0)["chat_id"]),
    ("thread", config.get_test_thread(0)["thread_id"]),
], ids=[
    "chat_id_p2p",  # 对应第一个参数组合
    "chat_id_group",  # 对应第二个参数组合
    "thread_id",  # 对应第三个参数组合
])
def container_info(request):
    return request.param
