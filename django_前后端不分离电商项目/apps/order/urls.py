# 匹配视图的方法
from django.conf.urls import url
from order.views import OrderPlaceView,OrderCommitView,OrderPayView
from order.views import CheckPayView, OrderCommentView

urlpatterns = [
    url(r'^place$', OrderPlaceView.as_view(), name='place'),
    url(r'^commit$', OrderCommitView.as_view(),name='commit'),
    url(r'^pay_order$', OrderPayView.as_view(), name='pay_order'),
    url(r'^check$', CheckPayView.as_view(), name='check'),
    url(r'^comment/(?P<order_id>\d.*)', OrderCommentView.as_view(), name='comment')
]