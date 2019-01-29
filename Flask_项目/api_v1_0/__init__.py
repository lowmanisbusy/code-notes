# coding=utf8

# 导入模块创建蓝图实例
from flask import Blueprint

api = Blueprint('api_v1_0', __name__)

# 需要将应用视图模块在这里进行导入, 否则蓝图并不知道视图的存在
from . import houses, users, orders, verify_code
