# coding=utf8

from celery import Celery
from . import config

# 创建celery应用对象
celery_app = Celery('ihome')

# 导入celery的配置信息
celery_app.config_from_object(config)

# 搜索celery异步任务, 在celery_task包下再定义具体需要实现异步任务的包, 通过进行自动搜索异步任务,当启动celery 工作者时,
# 就会监听所有的异步任务, send_sms这个包里定义了发送短信的任务,路径需要具体到send_sms,但是文件名必须是tasks.py
celery_app.autodiscover_tasks([
    "ihome.celery_task.send_sms"
])