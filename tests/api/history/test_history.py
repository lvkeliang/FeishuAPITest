import allure
import pytest
from typing import Dict, Any
from tests.client.client import feishu_client
from tests.test_data.case_loader import test_case_loader


# 装饰器标识container_id_type
def case_test_type(test_type):
    def decorator(func):
        func._test_type = test_type  # 附加属性
        return func

    return decorator


@pytest.fixture(scope="module")
def client():
    """共享的Feishu客户端fixture"""
    return feishu_client


@pytest.fixture
def prepared_test_case(request):
    """准备测试用例，执行setup并替换变量"""
    loader = test_case_loader
    test_case = request.param  # 从参数化获取测试用例

    # 1. 执行setup操作
    if test_case.setup:
        setup_context = loader.execute_setup(test_case.setup)
    else:
        setup_context = {}

    # 2. 替换请求中的变量
    # context = {"open_id": test_user["open_id"], **setup_context}
    context = {**setup_context}
    replaced_request = loader.replace_variables(test_case.request.dict(), context)

    yield {
        "request": replaced_request,
        "expected": test_case.expected.dict(),
        "context": context,
        "original_case": test_case
    }

    # 3. 测试结束后执行teardown
    if hasattr(request, "node") and hasattr(request.node, "funcargs"):
        response = request.node.funcargs.get("api_response")
        if response and test_case.teardown:
            loader.execute_teardown(test_case.teardown, response.json())


# 具体消息类型的测试
# @pytest.mark.skip(reason="正在开发其他的测试")
@case_test_type("common")
def test_history(client, prepared_test_case, container_info):
    container_id_type, container_id = container_info
    """通用历史消息测试"""
    with allure.step("Step 1: 准备测试用例"):
        test_data = prepared_test_case
        request_data = test_data["request"]

        # --- 动态注入参数 ---
        # 1. 注入 container_id_type 到查询参数
        query_params = request_data.get("query_params", {})
        query_params["container_id_type"] = container_id_type  # 覆盖或新增

        if test_data["original_case"].category == "positive":
            query_params["container_id"] = container_id  # 覆盖或新增

    with allure.step("Step 2: 发送请求"):
        # 发送请求
        response = client.request(
            method=request_data["method"],
            endpoint=request_data["endpoint"],
            params=request_data.get("query_params"),
            headers=request_data.get("headers"),
            json=request_data.get("body")
        )

    # 将响应保存到测试上下文中，供teardown使用
    pytest.api_response = response

    with allure.step("Step 3: 验证响应"):
        # 验证响应
        expected = test_data["expected"]

        # 1. 验证状态码
        assert response.status_code == expected["status_code"], \
            f"状态码不匹配，期望 {expected['status_code']}，实际 {response.status_code}"

        # 2. 验证响应头
        # if expected.get("headers"):
        #     for header, value in expected["headers"].items():
        #         assert header in response.headers, f"缺少响应头 {header}"
        #         assert response.headers[header] == value, \
        #             f"响应头 {header} 不匹配，期望 {value}，实际 {response.headers[header]}"

        # 3. 验证响应体
        # response_json = response.json()

        # 3.1 验证schema
        # if expected.get("schema"):
        #     validate_schema(response_json, expected["schema"])

        # 3.2 验证具体字段
        # if expected.get("body"):
        #     for field_path, expected_value in expected["body"].items():
        #         if field_path.startswith("@") and field_path.endswith("@"):
        #             # 特殊验证指令
        #             directive = field_path[1:-1]
        #             if directive == "contains":
        #                 assert expected_value in str(response_json), \
        #                     f"响应中未找到预期内容: {expected_value}"
        #         else:
        #             # 普通字段验证
        #             actual_value = _get_nested_value(response_json, field_path)
        #             assert actual_value == expected_value, \
        #                 f"字段 {field_path} 不匹配，期望 {expected_value}，实际 {actual_value}"


# 话题目前不支持通过strart_time和end_time来查询，当container_id_type为thread_id时，接口会无视strart_time和end_time这两个参数正常返回
# @pytest.mark.skip(reason="正在开发其他的测试")
@case_test_type("time")
def test_history_time(client, prepared_test_case, container_info):
    container_id_type, container_id = container_info
    """通用历史消息测试"""
    with allure.step("Step 1: 准备测试用例"):
        test_data = prepared_test_case
        request_data = test_data["request"]

        # --- 动态注入参数 ---
        # 1. 注入 container_id_type 到查询参数
        query_params = request_data.get("query_params", {})
        query_params["container_id_type"] = container_id_type  # 覆盖或新增

        if test_data["original_case"].category == "positive":
            query_params["container_id"] = container_id  # 覆盖或新增

    with allure.step("Step 2: 发送请求"):
        # 发送请求
        response = client.request(
            method=request_data["method"],
            endpoint=request_data["endpoint"],
            params=request_data.get("query_params"),
            headers=request_data.get("headers"),
            json=request_data.get("body")
        )

    # 将响应保存到测试上下文中，供teardown使用
    pytest.api_response = response

    with allure.step("Step 3: 验证响应"):
        # 验证响应
        expected = test_data["expected"]

        # 1. 验证状态码
        assert response.status_code == expected["status_code"], \
            f"状态码不匹配，期望 {expected['status_code']}，实际 {response.status_code}"


@case_test_type("pagination")
def test_history_pagination(client, prepared_test_case, container_info):
    container_id_type, container_id = container_info
    """验证分页参数一致性和排序稳定性"""
    with allure.step("Step 1: 准备测试用例"):
        test_data = prepared_test_case
        request_data = test_data["request"]

        # 动态注入参数
        query_params = request_data.get("query_params", {})
        query_params["container_id_type"] = container_id_type
        if test_data["original_case"].category == "positive":
            query_params["container_id"] = container_id

    with allure.step("Step 2: 首次请求（建立基准参数）"):
        # 记录初始参数
        original_sort = query_params.get("sort_type", "ByCreateTimeAsc")
        original_page_size = int(query_params.get("page_size", 20))

        print("首次请求参数")
        print("sort_type:", original_sort)
        print("page_size:", original_page_size)

        response1 = client.request(
            method=request_data["method"],
            endpoint=request_data["endpoint"],
            params=query_params,
            headers=request_data.get("headers")
        )
        data1 = response1.json()["data"]

        # 验证首屏数据
        assert data1["has_more"] is True, "应有更多数据"
        assert "page_token" in data1, "缺少分页令牌"
        assert len(data1["items"]) == original_page_size, f"预期返回{original_page_size}条数据"

    with allure.step("Step 3: 修改sort_type获取下一页（应保持原排序）"):
        # 第二页以及以后的排序方式都由page_token来决定保持与第一次的排序一样，所以指定的sort_type应该不会影响排序方式了
        modified_sort_params = query_params.copy()
        modified_sort_params["page_token"] = data1["page_token"]
        # 故意设置相反的排序方式
        modified_sort_params[
            "sort_type"] = "ByCreateTimeDesc" if original_sort == "ByCreateTimeAsc" else "ByCreateTimeAsc"

        print("修改sort_type参数")
        print("sort_type:", modified_sort_params.get("sort_type"))
        print("page_size:", modified_sort_params.get("page_size"))

        response2 = client.request(
            method=request_data["method"],
            endpoint=request_data["endpoint"],
            params=modified_sort_params,
            headers=request_data.get("headers")
        )
        data2 = response2.json()["data"]

        # 验证实际排序方式仍为原始排序
        first_page_last = data1["items"][-1]["create_time"]
        second_page_first = data2["items"][0]["create_time"]

        if original_sort == "ByCreateTimeAsc":
            assert first_page_last < second_page_first, "应保持升序排列"
        else:
            assert first_page_last > second_page_first, "应保持降序排列"

    with allure.step("Step 4: 修改page_size获取下一页"):
        # 分页依然可以正常修改page_size
        modified_size_params = query_params.copy()
        modified_size_params["page_token"] = data1["page_token"]
        modified_page_size = original_page_size + 2  # 改变分页大小
        modified_size_params["page_size"] = modified_page_size

        print("修改page_size参数")
        print("sort_type:", modified_size_params.get("sort_type"))
        print("page_size:", modified_size_params.get("page_size"))

        response3 = client.request(
            method=request_data["method"],
            endpoint=request_data["endpoint"],
            params=modified_size_params,
            headers=request_data.get("headers")
        )
        data3 = response3.json()["data"]

        # 验证实际返回数量为修改的page_size
        if not data3["has_more"]:
            assert len(data3["items"]) <= modified_page_size, f"预期返回{modified_page_size}条数据"


    with allure.step("Step 5: 正常分页验证连续性"):
        valid_params = query_params.copy()
        valid_params["page_token"] = data1["page_token"]

        print("正常分页参数")
        print("sort_type:", valid_params.get("sort_type"))
        print("page_size:", valid_params.get("page_size"))

        response4 = client.request(
            method=request_data["method"],
            endpoint=request_data["endpoint"],
            params=valid_params,
            headers=request_data.get("headers")
        )
        data4 = response4.json()["data"]

        # 验证全局排序一致性
        all_messages = data1["items"] + data4["items"]
        for i in range(len(all_messages) - 1):
            if original_sort == "ByCreateTimeAsc":
                assert all_messages[i]["create_time"] <= all_messages[i + 1]["create_time"]
            else:
                assert all_messages[i]["create_time"] >= all_messages[i + 1]["create_time"]

        # 末页验证
        if not data4["has_more"]:
            assert len(data4["items"]) <= original_page_size



# def history_pagination(client):
#     # 5. 异常分页测试（无效token）
#     with pytest.raises(APIError) as exc:
#         client.get(
#             "/open-apis/im/v1/messages",
#             params={
#                 "container_id_type": "chat",
#                 "container_id": chat_id,
#                 "page_token": "invalid_token_xxx"
#             },
#             headers={"Authorization": f"Bearer {token}"}
#         )
#     assert exc.value.code == 230001, "预期分页令牌错误"