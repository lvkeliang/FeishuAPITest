import pytest

from tests.test_data.case_loader import test_case_loader


def pytest_generate_tests(metafunc):
    if "prepared_test_case" in metafunc.fixturenames:
        # 从 mark 获取 msg_type
        msg_type = None
        for mark in metafunc.definition.iter_markers("msg_type"):
            msg_type = mark.args[0]
            break

        if not msg_type:
            pytest.skip("Test requires @pytest.mark.msg_type()")
        # 根据msg_type加载对应目录的JSON文件
        test_cases = test_case_loader.load_cases_by_type("messages", msg_type)
        # messages/text/positive/case1.json
        metafunc.parametrize(
            "prepared_test_case",
            test_cases,
            indirect=True,
            ids=lambda c: f"{c.category}_{c.name}"
        )
