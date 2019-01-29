"""daily_fresh URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin

# 匹配应用
urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    # 全文检索, 只需要在这里匹配路径, goods下面的search_indexes.py 会向数据库搜寻数据,并返回到templates/search/search.html中
    url(r'^search$', include('haystack.urls')),
    url(r'^tinymce/', include('tinymce.urls')), # 富文本编辑器
    # 因为已经在setting.py里设置了搜寻路径,所以不写apps,不用管标黄的报错
    url(r'^user/', include('user.urls', namespace='user')),  # 用户模块
    url(r'^cart/', include('cart.urls', namespace='cart')),  # 购物车模块
    url(r'^order/', include('order.urls', namespace='order')),  # 订单模块
    url(r'^', include('goods.urls', namespace='goods')),  # 商品模块
]
