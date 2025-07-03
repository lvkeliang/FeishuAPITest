# 快速开始指南

## 环境准备

1. 确保已安装Python 3.7+环境
2. 安装Allure报告工具（参考[这篇博客](https://blog.csdn.net/HUA6911/article/details/136911347)）

## 项目配置步骤

1. 克隆代码仓库：

   ```
   git clone https://github.com/lvkeliang/FeishuAPITest.git
   ```

2. 安装依赖库：

   可以运行下面的命令，通过项目中的requirements.txt进行安装

   ```
   pip install -r requirements.txt
   ```

3. 配置文件准备：

   - 进入`config`文件夹
   - 将`dev-example.yaml`重命名为`dev.yaml`
   - 将`config-example.yaml`重命名为`config.yaml`

4. 填写飞书API配置信息：

   - 打开`dev.yaml`文件
   - 在`test_accounts`部分填写你的飞书`open_id`[如何获取？详见快速获取Open ID](#快速获取Open ID)这个会控制你的机器人向哪个用户发送消息
   - 在`feishu`部分填写你的飞书应用的`app_id`和`app_secret`[如何获取？详见获取APP ID和APP SECRET](#获取APP ID和APP SECRET)
   
   ![dev.yaml部分示例](https://picture-0-1320983848.cos.ap-chongqing.myqcloud.com/blog/20250703090939.png)

## 运行测试

执行以下命令运行测试并生成报告：

```shell
pytest tests/api/test_message.py -v --alluredir=./reports/allure --html=reports/html/report.html --self-contained-html -rA
```

至此，该项目应该可以成功运行了

除此之外，你可以将项目文件夹的`FeishuAPITest/tests/test_data/`中的json文件里面的一些文件地址替换为你自己的本地文件地址以能够正常上传图片、读取文件等

## 查看报告

经过上面一步，成功运行测试后，pytest应该已经在`FeishuAPITest/reports`文件夹下生成了测试报告，想要美观的查看报告，可以打开里面的html文件，或者运行下面的命令，使用allure进行更人性化的查看（需要先安装allure，详见[环境准备](#环境准备)）：

```shell
allure serve reports/allure
```

## 快速获取Open ID

1. 访问[发送消息 - 服务端 API - 开发文档 - 飞书开放平台](https://open.feishu.cn/document/server-docs/im-v1/message/create)
2. 在右侧查询参数选项中选择`open_id`

![选择open_id](https://picture-0-1320983848.cos.ap-chongqing.myqcloud.com/blog/20250703091743.png)

3. 点击快速复制`open_id`

![快速复制open_id](https://picture-0-1320983848.cos.ap-chongqing.myqcloud.com/blog/20250703092015.png)

4. 在其中搜索并选择你想要复制的成员的`open_id`并点击**复制成员ID**

详细更多方法请参考[如何获取用户的 Open ID - 开发指南 - 开发文档 - 飞书开放平台](https://open.feishu.cn/document/faq/trouble-shooting/how-to-obtain-openid)

## 获取APP ID和APP SECRET

1. 访问[飞书开放平台](https://open.feishu.cn/app/)
2. 进入"飞书QA训练营演示企业"的应用后台，进入对应的应用
3. 在"凭证与基础信息"中获取`app_id`和`app_secret`

## 注意事项

1. 必须使用加入了"飞书QA训练营演示企业"的账号登录
2. 确保你已被添加为应用的协作人员
3. IDE建议使用PyCharm，有人使用TREA遇到了环境问题，这个有待验证
4. 测试运行后，机器人会向配置的open_id发送消息
5. 协作开发上，修改代码以及进行git commit之前，记得先进行pull操作，避免出现与他人开发的代码冲突，确认没有问题了再push上去
