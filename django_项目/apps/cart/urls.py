# 匹配视图的方法
from django.conf.urls import url
from cart.views import CartAddView, CartInfoView, CartUpdateView, CartDeleteView

urlpatterns = [
    # 购物车商品添加
    url(r'^$', CartInfoView.as_view(), name='show'),
    url(r'^add$', CartAddView.as_view(), name='add'),
    url(r'^update$', CartUpdateView.as_view(), name='update'),
    url(r'^delete$', CartDeleteView.as_view(), name='delete')
]