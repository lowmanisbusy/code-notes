# coding=utf8

# 设置中间者
broker_url = "redis://127.0.0.1:6379/13"

# 当使用celery执行任务后, 如果需要返回值,还需要使用redis接收这个返回值,
result_backend = "redis://127.0.0.1:6379/12"
