import pytest

from tests.test_data.case_loader import test_case_loader

import pytest
from tests.test_data.case_loader import test_case_loader
from tests.utils.config_loader import config


def pytest_generate_tests(metafunc):
    if "prepared_test_case" in metafunc.fixturenames:
        # 从测试函数提取msg_type
        msg_type = getattr(metafunc.function, "_msg_type", None)

        if not msg_type:
            pytest.skip(f"Cannot determine msg_type from test name: {metafunc.definition.name}")

        test_cases = test_case_loader.load_cases_by_type("message", msg_type)
        metafunc.parametrize(
            "prepared_test_case",
            test_cases,
            indirect=True,
            ids=lambda c: f"{c.category}_{c.name}"
        )


@pytest.fixture(params=[
    ("open_id", config.get_test_account(0)["open_id"]),
    ("union_id", config.get_test_account(0)["union_id"]),
    ("user_id", config.get_test_account(0)["user_id"]),
    # ("email", config.get_test_account(0)["email"]),
    ("chat_id", config.get_test_group(0)["chat_id"]),
], ids=[
    "open_id",  # 对应第一个参数组合
    "union_id",  # 对应第二个参数组合
    "user_id",   # 对应第三个参数组合
    # "email",     # 对应第四个参数组合
    "chat_id",   # 对应第五个参数组合
])
def receiver_info(request):
    return request.param

# def pytest_generate_tests(metafunc):
#     if "prepared_test_case" in metafunc.fixturenames:
#         # 从 mark 获取 msg_type
#         msg_type = None
#         for mark in metafunc.definition.iter_markers("msg_type"):
#             msg_type = mark.args[0]
#             break
#
#         if not msg_type:
#             pytest.skip("Test requires @pytest.mark.msg_type()")
#
#         test_cases = test_case_loader.load_cases_by_type("messages", msg_type)
#         metafunc.parametrize(
#             "prepared_test_case",
#             test_cases,
#             indirect=True,
#             ids=lambda c: f"{c.category}_{c.name}"
#         )
