# coding=utf8

import redis  # 导入redis
import logging  # 日志记录使用到
from logging.handlers import RotatingFileHandler  # 日志记录使用到

from flask import Flask  # 导入Flask用以创建核心应用
from flask_sqlalchemy import SQLAlchemy  # 导入sqlalchemy 为项目连接mysql提供orm
from flask_session import Session  # 用以设置session
from flask_wtf import CSRFProtect  # 用以进行csrt验证

from config import config_map  # 从config.py中导入config_map 以便选择不同的配置选项
from ihome.utils import common_reconverter

# 创建数据库工具
# 因为在manage.py中,需要同事导入create_app 和db 所以在create_app 再完成核心应用参数app的传递, 避免循环导入
db = SQLAlchemy()

# 创建redis连接实例, 因为需要在视图应用中调用这个应用实例, 所以把它定义成全局变量, 便于调用
# 开发环境和线上环境会使用不同的redis数据库, 所以需要在工厂函数中进行设定
redis_store = None

# 设置日志的记录等级
logging.basicConfig(level=logging.DEBUG)  # 调试 debug级, 如果是debug模式, 将会记录所有的输出信息

# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024*1024*100, backupCount=10)

# 创建日志记录的格式                日志等级    输入日志信息的文件名 行数    日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')

# 为刚创建的日志记录器设置日志记录格式
file_log_handler.setFormatter(formatter)

# 为全局的日志工具对象（flask app使用的）添加日记录器
logging.getLogger().addHandler(file_log_handler)


# 使用工厂模式, 根据需求使用不同的配置信息, 生成相应的项目核心应用实例app
# 在工厂函数里进行配置的信息,都是一些需要将项目核心应用实例app进行传参的选项, 或者需要确定项目使用环境后才能选择确定的配置
def create_app(run_name):  # run_name在引用时进行传参
    """工厂函数, 用来创建flask应用对象
    :param run_name: flask运行的模式名字， product-生产模式  develop-开发模式
    """
    app = Flask(__name__)
    # 指定配置信息
    app.config.from_object(config_map[run_name])

    # 已创建app, 将数据库对象db 进行初始化
    db.init_app(app)

    # 声明使用全局变量
    global redis_store
    # 调用不同配置环境的redis连接实例
    redis_store = redis.StrictRedis(host=config_map[run_name].REDIS_HOST,
                                    port=config_map[run_name].REDIS_PORT,
                                    db=config_map[run_name].REDIS_DB)
    # session
    # flask-session扩展  pip install flask-session
    # 对flask_session扩展初始化
    # 对flask_session扩展初始化, 因为已经向app对象注册了配置信息, 所以在生成Session()对象时传递app引用, 可以将session相关配置信息添加到Session类中, 修改Session类的属性
    Session(app)

    # 补充csrf防护
    # 防护机制
    # 对于包含了请求体的请求（POST、PUT、DELETE），从请求的cookie中读取一个csrf_token的值，
    # 从请求体重读取一个csrf_token的值，进行比较，如果相同，则允许访问，否则返回403错误
    CSRFProtect(app)

    # 注册自定义的转换器
    app.url_map.converters['re'] = common_reconverter.Reconverter

    # 注册返回静态页面视图的蓝图,记得先把返回静态页面蓝图进行注册
    from ihome import web_html_page
    app.register_blueprint(web_html_page.html)

    # 注册接口蓝图
    from ihome import api_v1_0  # 指定访问应用视图路径的前缀
    app.register_blueprint(api_v1_0.api, url_prefix='/api/v1.0')

    # 返回应用实例
    return app


# 与上下配置项没有逻辑关系的, 配置顺序可以更改, 但凡需要使用app的都必须在创建了app之后进行配置
