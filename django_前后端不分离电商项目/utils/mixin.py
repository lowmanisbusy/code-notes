# 导入通用类视图 as_view() 是其中一个方法
from django.views.generic import View

# 导入装饰器类,导入django认证系统的登录状态识别的装饰器的模块
# (能识别用户是否登录,进行用户中心操作时,如果没有登录,则重定向到登录页面)
from django.contrib.auth.decorators import login_required


class LoginRequiredView(View):
    # 类方法
    @classmethod
    # 重写as_view()方法
    def as_view(cls, **initkwargs):
        # 调用View父类的as_view方法
        view = super(LoginRequiredView, cls).as_view(**initkwargs)
        # 调用登录判断装饰器
        return login_required(view)


class LoginRequiredViewMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        # 调用View父类的as_view方法,
        view = super(LoginRequiredViewMixin, cls).as_view(**initkwargs)
        # 调用登录判断装饰器
        return login_required(view)



# 在应用下的urls.py中, 使用类视图直接调用了as_view()父类方法,如UserInfoView.as_view(),相当于返回了login_required(view)
# 也就是说用 @login_required 装饰了 as_view()