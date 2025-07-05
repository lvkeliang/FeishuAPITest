import os
from pathlib import Path

from requests_toolbelt import MultipartEncoder

import requests
from typing import Dict, Any, Optional, Union
from tests.utils.config_loader import config


def _log_request(response: requests.Response):
    """记录请求和响应日志"""
    request = response.request
    print("\n=== Request Details ===")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print("Headers:")
    for k, v in request.headers.items():
        print(f"  {k}: {v}")

    if request.body:
        print("Body:")
        try:
            if isinstance(request.body, bytes):
                print(request.body.decode('utf-8'))
            else:
                print(request.body)
        except UnicodeDecodeError:
            print("<binary data>")

    print("\n=== Response Details ===")
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for k, v in response.headers.items():
        print(f"  {k}: {v}")
    try:
        print("Body:", response.json())
    except ValueError:
        print("Body:", response.text)


class FeishuClient:
    def __init__(self):
        self.base_url = config.env_config["feishu"]["base_url"]
        # 优先使用配置文件中的 tenant_access_token
        self._tenant_access_token = config.env_config["feishu"].get("tenant_access_token")
        self.token_expire = config.env_config["feishu"]["token_expire"]
        self.timeout = config.config["testing"]["timeout"]

    @property
    def tenant_access_token(self) -> str:
        """获取或刷新tenant_access_token"""
        # 如果已经有token（比如配置文件提供），直接用
        if self._tenant_access_token:
            return self._tenant_access_token
        # 否则自动获取
        self.refresh_token()
        return self._tenant_access_token

    def refresh_token(self):
        """刷新access token"""
        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": config.env_config["feishu"]["app_id"],
            "app_secret": config.env_config["feishu"]["app_secret"]
        }
        response = requests.post(
            url,
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        self._tenant_access_token = response.json()["tenant_access_token"]

    def send_message(
            self,
            method: str,
            endpoint: str,
            params: Optional[Dict[str, Any]] = None,
            json: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> requests.Response:
        """发送API请求"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json"
        }

        # 合并自定义headers
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        response = requests.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            json=json,
            timeout=self.timeout,
            **kwargs
        )

        print("Request:", response.request.body)  # 查看实际发送的内容
        print("Response:", response.text)  # 查看飞书返回的具体错误

        return response

    def upload_image(
            self,
            image_path: Union[str, Path],
            image_type: str = "message",  # "message(用于发送消息)"|"avatar(用于设置头像)"
            endpoint: str = "/open-apis/im/v1/images",
            **kwargs
    ) -> requests.Response:
        """
        上传图片并返回image_key
        :param image_path: 图片路径
        :param image_type: 图片类型 ("message"|"avatar")
        :param endpoint: 接口路径
        :return: 飞书返回的image_key
        :raises: FileNotFoundError, FileUploadError
        """

        """发送API请求"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
        }

        # 合并自定义headers
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        # 使用 MultipartEncoder 构造请求体
        multipart_form = MultipartEncoder(
            fields={
                'image_type': image_type,
                'image': (os.path.basename(image_path), open(image_path, 'rb'), 'image/jpeg')
            }
        )

        # 添加 Content-Type 头，由 MultipartEncoder 自动生成
        headers['Content-Type'] = multipart_form.content_type

        with open(image_path, 'rb') as f:
            response = requests.post(
                url,
                headers=headers,
                data=multipart_form,
                timeout=self.timeout
            )

        response.raise_for_status()
        return response.json()["data"]["image_key"]

    def request(
            self,
            method: str,
            endpoint: str,
            *,
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, Any]] = None,
            json: Optional[Dict[str, Any]] = None,
            data: Optional[Union[Dict[str, Any], bytes, str]] = None,
            files: Optional[Dict[str, Any]] = None,
            timeout: Optional[float] = None,
            **kwargs
    ) -> requests.Response:
        """
        通用的飞书API请求方法

        参数:
            method: HTTP方法 (GET, POST, PUT, DELETE等)
            endpoint: API端点 (如 "/open-apis/im/v1/messages")
            params: URL查询参数
            headers: 自定义请求头
            json: JSON格式的请求体
            data: 表单数据或原始请求体
            files: 文件上传 {'field': (filename, fileobj, content_type)}
            timeout: 超时时间(秒)
            **kwargs: 其他requests.request支持的参数

        返回:
            requests.Response对象

        示例:
            # 发送JSON请求
            client.request(
                method="POST",
                endpoint="/open-apis/im/v1/messages",
                json={"msg_type": "text", "content": {"text": "Hello"}}
            )

            # 上传文件
            client.request(
                method="POST",
                endpoint="/open-apis/image/v4/put/",
                files={'image': ('test.jpg', open('test.jpg', 'rb'), 'image/jpeg')}
            )
        """
        # 构造完整URL
        url = f"{self.base_url}{endpoint}"

        # 设置默认请求头
        # default_headers = {"Authorization": f"Bearer {self.tenant_access_token}"}
        default_headers = {}

        # 合并自定义headers
        final_headers = {**default_headers, **(headers or {})}

        # 自动处理multipart/form-data
        if files and 'Content-Type' not in final_headers:
            # 如果上传文件且未指定Content-Type，让requests自动生成
            final_headers.pop('Content-Type', None)

        # 发送请求
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                headers=final_headers,
                json=json,
                data=data,
                files=files,
                timeout=timeout or self.timeout,
                **kwargs
            )

            # 调试日志
            _log_request(response)

            return response

        except requests.exceptions.RequestException as e:
            # 封装请求异常
            raise FeishuRequestError(f"Request failed: {str(e)}") from e


class FeishuRequestError(Exception):
    """飞书API请求异常"""
    pass


# 全局客户端
feishu_client = FeishuClient()
