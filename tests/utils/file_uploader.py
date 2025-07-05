import os
import mimetypes
import json
from pathlib import Path
from typing import Union

import requests


class FileUploadError(Exception):
    """自定义上传异常"""
    pass


class FileUploader:
    def __init__(self, client):
        self.client = client

    def upload_image(
            self,
            image_path: Union[str, Path],
            image_type: str = "message"
    ) -> str:
        """
        上传图片并返回image_key
        :param image_path: 图片路径
        :param image_type: 图片类型 ("message"|"avatar")
        :return: 飞书返回的image_key
        :raises: FileNotFoundError, FileUploadError
        """
        # 1. 验证文件存在性
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        # 2. 调用client的上传接口
        response = self.client.upload_image(
            endpoint="/open-apis/im/v1/images",
            image_path=image_path,
            image_type=image_type
        )

        return response["data"]["image_key"]

