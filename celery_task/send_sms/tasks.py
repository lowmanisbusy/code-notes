# coding=utf8

# 导入celery的应用对象
from ihome.celery_task.main import celery_app
# 导入发送短信的方法
from ihome.libs.yuntongxun.send_sms import CCP


# 使用celery的装饰器进行装饰, 执行可能有耗时步骤的方法
@celery_app.task
def send_sms(to, datas, temp_id):
    """发送短信的异步任务"""
    ccp = CCP()
    # 这个返回值需要使用redis进行接收,celery自动返回,已经在config进行了设置使用redis接收返回值
    result = ccp.send_template_sms(to,datas, temp_id)
    # 将发送短信结果返回给调用者, 在视图中调用本方法, 调用方式 send_sms.delay(参数1,参数2,参数3)
    return result
