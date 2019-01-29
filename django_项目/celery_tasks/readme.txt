

    # 去到celery_tasks文件夹所在的父级目录下,(工作者可以不再同一个主机下, 但是需要将项目代码复制到运行着worker的主机上),使用django环境
    注意celery 启动所需要的路径
    # 启动中间人,这里使用redis服务器(在代码中设置好redis的ip地址,端口号,lacalhost(127.0.0.1)只能本机连接)
    # 进入安装了redis 和 celery 的虚拟环境 运行工作者
    # 输入命令 celery -A celery_tasks.tasks worker -l info  命令不要写错(celery会自动到celery_tasks文件夹的tasks.py寻找app,也可以加上app celery_tasks.tasks.app)
    # 运行工作者, 后面两个参数的意思按级别显示运行的相关的信息 第三个参数就是设置的任务名称创建celery类时对应的名字