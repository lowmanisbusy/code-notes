# coding=utf8

from werkzeug.routing import BaseConverter


# 定义一个用以配置html静态页面的转换器(因为是前后端分离, 所以需要专门定义一个视图用以返回页面)
class Reconverter(BaseConverter):
    """自定义正则转换器"""
    def __init__(self, url_map, regex):  # 第二个参数是flask自动传进来的, 父方法需要, 第二个是开发者传递进来的正则
        super(Reconverter, self).__init__(url_map)
        self.regex = regex