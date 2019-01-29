# coding=utf8

import functools  # 这个工具, 是为了在装饰器中,在装饰时,不改变被装饰函数的各种属性

from flask import session, jsonify, g  # 使用g 应用上下文将参数传递到视图中
from ihome.utils.response_code import RET


# 创建装饰器
def login_required(view_func):
    """验证用户是否登录的装饰器
    因为是前后端分离, 所以当用户未登录时,不决定返回到登录前页面, 这个功能通过前端实现
    """
    @functools.wraps(view_func)
    def wrapper(*args, **kwargs):
        # 判断用户的登录状态
        user_id = session.get('user_id')
        if user_id is not None:
            # 将user_id保存到g对象中，方便视图函数直接使用
            g.user_id = user_id
            return view_func(*args, **kwargs)
        else:
            # 如果用户未登录，返回json数据，告知前端
            return jsonify(errcode=RET.SESSIONERR, errmsg='用户未登录')
    return wrapper







# def demo_decorate(func):
#     """装饰器说明"""
#     # warps的作用是将wrapper函数的相关属性恢复设置为被装饰函数func的属性
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         """装饰器内层函数说明"""
#         pass
#
#     return wrapper


# # 实现原理
# # def demo_decorate(func):
# #     """装饰器说明"""
# #     def wrapper(*args, **kwargs):
# #         """装饰器内层函数说明"""
# #         pass
# #
# #     wrapper.__name__ = func.__name__  # 自己直接手动修改装饰函数的属性,也可还原被装饰函数的属性
# #     wrapper.__doc__ = func.__doc__
# #
# #     return wrapper
#
#
# @demo_decorate    # itcast -> wrapper
# def itcast():
#     """itcast说明信息"""
#     pass
#
#
# if __name__ == '__main__':
#     print(itcast.__name__)  # 函数的名字
#     print(itcast.__doc__)  # 函数的说明文档