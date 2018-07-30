这是定义一个完整的celery异步任务队列的包, celery配置在这个包里的config.py
进入ihome包所在目录下, 使用以下命令启动celery, 因为需要和所导入的需要进行异步执行的celery应用对象的绝对路径保持一致,

如本例中,在 celery_task.send_sms/tasks.py 中通过下面的的使用绝对路径的方式导入了 celery的应用对象:

from ihome.celery_task.main import celery_app

所以需要去ihome所在目录下使用如下命令启动, 否则找不到任务函数

celery -A ihome.celery_task.main worker -l info
