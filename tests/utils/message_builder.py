import json


class MessageBuilder:
    @staticmethod
    def build_text(content="测试文本"):
        return json.dumps({"text": content})

    @staticmethod
    def build_post():
        # 构建符合飞书要求的富文本结构
        post_content = {
            "zh_cn": {
                "title": "测试富文本标题",
                "content": [
                    [
                        {"tag": "text", "text": "第一行: ", "style": ["bold"]},
                        {"tag": "a", "text": "飞书官网", "href": "https://www.feishu.cn"}
                    ],
                    [{"tag": "text", "text": "这是一段测试文本"}],
                    [{"tag": "hr"}]
                ]
            }
        }

        # JSON编码
        return json.dumps(post_content)

    @staticmethod
    def build_image(uploader):
        # with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        #    tmp.write(b'\x89PNG\x0D\x0A\x1A\x0A\x00\x00\x00\x0D...')  # 生成测试图片
        #    return json.dumps({"image_key": uploader.upload_image(tmp.name)})
        return json.dumps({"image_key": uploader.upload_image("F:\\pictures\\mountainschool2.jpg")})

    @staticmethod
    def build_interactive():
        return "{\"schema\":\"2.0\",\"config\":{\"update_multi\":true,\"style\":{\"text_size\":{\"normal_v2\":{" \
               "\"default\":\"normal\",\"pc\":\"normal\",\"mobile\":\"heading\"}}}},\"body\":{" \
               "\"direction\":\"vertical\",\"padding\":\"12px 12px 12px 12px\",\"elements\":[{\"tag\":\"markdown\"," \
               "\"content\":\"西湖，位于中国浙江省杭州市西湖区龙井路1号，杭州市区西部，汇水面积为21.22平方千米，湖面面积为6.38平方千米。\",\"text_align\":\"left\"," \
               "\"text_size\":\"normal_v2\",\"margin\":\"0px 0px 0px 0px\"},{\"tag\":\"button\",\"text\":{" \
               "\"tag\":\"plain_text\",\"content\":\"🌞更多景点介绍\"},\"type\":\"default\",\"width\":\"default\"," \
               "\"size\":\"medium\",\"behaviors\":[{\"type\":\"open_url\"," \
               "\"default_url\":\"https://baike.baidu.com/item/%E8%A5%BF%E6%B9%96/4668821\",\"pc_url\":\"\"," \
               "\"ios_url\":\"\",\"android_url\":\"\"}],\"margin\":\"0px 0px 0px 0px\"}]},\"header\":{\"title\":{" \
               "\"tag\":\"plain_text\",\"content\":\"今日旅游推荐(测试卡片)\"},\"subtitle\":{\"tag\":\"plain_text\"," \
               "\"content\":\"\"},\"template\":\"blue\",\"padding\":\"12px 12px 12px 12px\"}}"
        # return json.dumps({
        #     "config": {"wide_screen_mode": True},
        #     "elements": [{
        #         "tag": "div",
        #         "text": {"tag": "plain_text", "content": "测试卡片内容"}
        #     }]
        # })
