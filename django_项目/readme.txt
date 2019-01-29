pip install uwsgi
uwsgi.ini 这个文件是uwsgi服务器的配置文件, 使用uwsgi服务器,需要先在settings设置:
DEBUG=FALSE
ALLOWED_HOSTS=[‘*’]
启动:uwsgi –-ini 配置文件路径 例如:uwsgi --ini uwsgi.ini
停止:uwsgi --stop uwsgi.pid路径 例如:uwsgi --stop uwsgi.pid
在实际项目中,会拷贝多份项目代码,运行在不同uwsgi服务器上,再通过配置好调度服务器nginx的conf文件,从而实现nginx调度服务器轮流调用不同的uwsgi服务器,实现负载均衡
在django项目中使用pymysql与mysql进行交互时,需要在项目的配置包里的__init__.py 导入相关文件
