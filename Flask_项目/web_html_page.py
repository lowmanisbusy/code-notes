# coding=utf8

from flask import Blueprint, make_response
from flask import current_app
from flask_wtf import csrf

# 创建蓝图
html = Blueprint('html', __name__)


# 定义视图, 返回静态页面
@html.route('/<re(r".*"):file_name>')
def get_html_file(file_name):
    """返回静态页面"""
    # 只要域名后面只带/ 或者带/+相应字符串, 就到html目录中找到文件并返回给用户

    if not file_name:
        file_name = 'index.html'

    if file_name != "favicon.ico":
        file_name = 'html/' + file_name

    # 使用方法 send_static_file(静态目录中的文件名)，函数会自动去静态目录中找文件，返回包含文件内容的响应信息
    # 使用make_response() 可以将数据返回给客户端, 使用make_response()返回一个对象, 使用这个对象可以设置cookie等
    resp = make_response(current_app.send_static_file(file_name))

    # 生成csrf_token随机字符串的值
    csrf_token = csrf.generate_csrf()

    # 将csrf_token设置到cookie当中, 不写过期时间, 关闭客户端就失效
    resp.set_cookie('csrf_token', csrf_token)
    return resp
