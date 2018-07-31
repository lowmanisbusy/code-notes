# 匹配视图的方法,及类视图

# 导入相关模型
from django.conf.urls import url
from apps.user.views import RegisterView, ActiveView, LoginView, LogoutView, UserInfoView, UserOrderView, AddressView

# 导入django认证系统的登录状态识别的装饰器的模块
# (能识别用户是否登录,进行用户中心操作时,如果没有登录,则重定向到登录页面)
from django.contrib.auth.decorators import login_required

urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'),  # 匹配注册视图; 并进行命名,以便进行反向解析
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),  # 匹配发送给用户的激活链接
    url(r'^login$', LoginView.as_view(), name='login'),  # 登录页面
    url(r'^logout$', LogoutView.as_view(), name='logout'),  # 登出操作

    # 手动调用login_required装饰器，相当于得到的是login_required装饰器的返回值
    # 返回用户中心个人信息, 使用该方法后,会在提交登录请求的地址栏增加next参数,记录着在那个页面请求需要登录的操作,所以需要
    # 在登录视图取到该参数,再进行重定向
    # url(r'^$', login_required(UserInfoView.as_view()), name='user'),
    # 返回个人订单页
    # url(r'^user/oder', login_required(UserOrderView.as_view()), name='order'),
    # 返回个人地址页
    # url(r'^user/address$', login_required(AddressView.as_view()), name='address'),

    # 在登录视图取到该参数,再进行重定向,重写了父类的as_view()方法,详细参考 utils包的mixin模块
    url(r'^$', UserInfoView.as_view(), name='user'),
    # 返回个人订单页
    url(r'^order/(?P<page>\d+)$', UserOrderView.as_view(), name='order'),
    # 返回个人地址页
    url(r'^address$', AddressView.as_view(), name='address'),
]
