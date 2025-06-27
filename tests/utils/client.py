import os
from pathlib import Path

from requests_toolbelt import MultipartEncoder

import requests
from typing import Dict, Any, Optional, Union
from tests.utils.config_loader import config



class FeishuClient:
    def __init__(self):
        self.base_url = config.env_config["feishu"]["base_url"]
        self._tenant_access_token = None
        self.token_expire = config.env_config["feishu"]["token_expire"]
        self.timeout = config.config["testing"]["timeout"]

    @property
    def tenant_access_token(self) -> str:
        """获取或刷新tenant_access_token"""
        if not self._tenant_access_token:
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
            endpoint: str,
            image_path: Union[str, Path],
            image_type: str = "message",  # "message(用于发送消息)"|"avatar(用于设置头像)"
            **kwargs
    ) -> requests.Response:
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
        return response.json()

