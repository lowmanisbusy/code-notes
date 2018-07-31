from django.shortcuts import render, redirect  # 返回应答,反解析
from django.core.urlresolvers import reverse  # 用来进行反解析操作
from django.core.mail import send_mail  # 使用这个模块进行发送邮件操作
from django.http import HttpResponse
from django.views.generic import View  # 导入通用类视图 后面的View v大写
from django.conf import settings
from django.contrib.auth import authenticate, login, logout  # 通过导入django认证系统的这三个模块,进行用户身份确认,登录,登出操作
from django.core.paginator import Paginator

# 导入正则
import re
# 因为在setting.py 中导入的默认搜寻路径,所以虽然报错,但是可以导入. 如果修改,无法访问,为什么.
from user.models import User, Address
from goods.models import GoodsSKU
from order.models import OrderInfo,OrderGoods
# 导入itsdangerous包里的方法,进行数据签名
from itsdangerous import TimedJSONWebSignatureSerializer as make_sign
# 用来捕捉激活连接的签名是否过期
from itsdangerous import SignatureExpired
# 导入发送激活邮件的模块celery
from celery_tasks.tasks import send_register_active_email
# 导入redis相关模块,和redis数据库进行交互
from redis import StrictRedis
# 导入自定的装饰器类
from utils.mixin import LoginRequiredView, LoginRequiredViewMixin


# 定义注册类视图 路径是/user/register
class RegisterView(View):
    """如果是get请求就就返回这个视图下的get方法 进行返回注册页面 否侧就是post请求,提交表单"""
    def get(self, request):
        return render(request, 'register.html')

    # 接收post请求
    def post(self, request):
        # 第一步:接收参数  第二步:参数校验 第三步:业务处理 第四步:返回应答
        # 接收参数
        username = request.POST.get('user_name') # 接收用户名
        password = request.POST.get('pwd') # 接收密码
        c_password = request.POST.get('cpwd') # 接收确认密码
        email = request.POST.get('email') # 接收邮箱
        allow = request.POST.get('allow') # 是否同意协议, 同意的话,提交的为'on",不同意则不提交值

        # 参数校验
        # 校验参数完整性,使用all()方法,只有当列表里的参数全部存在时,才返回真
        if not all([username, password, c_password, email]):
            return render(request, 'register.html', {'errmsg': '请将信息填写完整再进行注册'})
        # 校验两次密码是否一致
        if password != c_password:
            return render(request, 'register.html', {'errmsg': '两次输入的密码不一致'})
        # 校验是否同意协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请阅读协议,并选择同意'})
        # 校验邮箱,使用正则
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不合法'})
        # 校验用户名是否已被注册
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            return render(request, 'register.html', {'errmsg': '用户名已被注册'})
        # 业务处理 使用django自带的认证系统的create_user()方法,创建一个用户,并往数据表保存数据,返回一个用户对象
        user = User.objects.create_user(username, email, password)
        # 使用create_user()方法,会自动修改is_active()参数为1,即是激活状态,需要改为零
        user.is_active = 0
        user.save()

        # 加密用户的身份信息，生成激活token itsdangerous, 防止非法者利用连接进行非法攻击
        # 使用django settings.py里的秘钥
        sign = make_sign(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        # 加密数据,是二进制的数据
        token = sign.dumps(info)
        # 解码,转换成str
        token = token.decode()

        # # 组织发送内容
        # # 邮件标题
        # subject = '天天生鲜欢迎您'
        # # 邮件正文,此处设置为空
        # message = ''
        # # 邮件发送方
        # sender = settings.EMAIL_FROM
        # # 邮件接收方,将所有接收方存放在一个列表里
        # receiver = [email]
        # # 要发送的链接
        # send_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击以下链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (
        # username, token, token)
        # # 发送邮件,将message 赋值给html_message 可以将内容在客户端以html文本显示
        # send_mail(subject, message, sender, receiver, html_message=send_message)
        # 是否应该输入手机号码进行确认输入验证码后再进行发送邮件,发送邮件成功后是否应该通知用户发送成功,并提醒用户激活账号

        #  调用发送激活邮件的方法,向celery的异步队列添加发送邮件的任务,可以异步执行耗时操作,提高用户体验,优化程序性能
        # 方法从celery_tasks.tasks 导入
        send_register_active_email.delay(email, username, token)

        # 发送成功后返回应答,使用redirect()重定向,reverse()反解析
        return redirect(reverse('user:login'))


# 当用户进行激活账号时,处理用户的激活请求  /user/active/激活token信息
class ActiveView(View):
    """激活账号"""
    def get(self, request, token):
        # from itsdangerous import TimedJSONWebSignatureSerializer as make_sign
        # 在处理添加了签名的激活信息时,必须相同的密钥,相同的过期时间
        sign = make_sign(settings.SECRET_KEY, 3600)
        try:
            # 解密数据
            info = sign.loads(token)
            user_id = info['confirm']
            # 业务处理,通过取得的user_id 取得相关用户的对象,并修改信息
            user = User.objects.get(id=user_id)
            # 将用户激活
            user.is_active = 1
            # 保存数据到数据库
            user.save()
            # 返回应答跳转到登录页面
            return redirect(reverse('user:login'))
        except SignatureExpired:
            # 激活链接已失效
            # 实际开发:
            return HttpResponse('激活链接已失效')


# django框架会给request对象增加一个属性user
# 如果用户已经登录，user是认证系统用户模型类（User)的实例对象
# 如果用户没有登录，user是AnonymousUser类的实例对象
# 在模板文件中可以直接使用request的user属性
class LoginView(View):
    """登录"""
    def get(self, request):
        """显示登录页面"""
        # 获取在请求过程中传递回来的cookie
        if 'username' in request.COOKIES:
            username = request.COOKIES['username']
            # 如果用户在请求登录页面时发送了带有username的cookie,说明用户选择记住了用户名,应该将相应的html标签改为checked
            checked = 'checked'
        else:
            # 没有发送用户名过来,将两个空字符串传递回去
            username = ''
            checked = ''
        return render(request, 'login.html', {'username':username, 'checked': checked})

    def post(self, request):
        """提交登录信息"""
        # 获取参数
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remember = request.POST.get('remember')
        # 参数校验
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '请填写用户名和密码'})
        # 业务处理
        # 根据用户名和密码查找用户信息,使用django认证系统的authenticate(username=username, password=password)
        # 方法,判断用户是否存在
        user = authenticate(username=username, password=password)
        # 进行判断
        if user is not None:
            # 进行判断账户是否已经激活
            if user.is_active:
                # 用户已激活, 允许登录,使用login()方法,记录登录状态,这是django自带的认证系统的一个方法,会自己创建session,参数必须传入
                # 如果自己自己创建session   request.session[键]=值,  request.session.set_expiry(value)
                # 如果value是一个整数，会话将在value秒没有活动后过期。
                # 如果value为0，那么用户会话的Cookie将在用户的浏览器关闭时过期。
                # 如果value为None，那么会话永不过期。
                # 如果没有指定过期时间则两个星期后过期。
                login(request, user)
                # 获取登录后要跳转到的next地址, 默认跳转到首页 /user/login?next=参数
                next_url = request.GET.get('next', reverse('goods:index'))
                # print(next_url)
                # 跳转到next_url网址
                # redirect()是HttpResponseRedirect的方法, HttpResponseRedirect是HttpResponse的子类, 最终返回的是一个response对象
                # 在提交表单的模板html form表单中,不设置action,就会使用地址栏的地址进行提交,这样才能将参数传递过来
                response = redirect(next_url)
                # 判断是否需要记住用户名
                if remember=="on":
                    # 设置一个cookie信息，来保存用户的用户名
                    # 设置cookie需要调用set_cookie方式，set_cookie它是HttpResponse对象的方法
                    # HttpResponseRedirect是HttpResponse的子类
                    response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    # 否则删除cookie,取消记住用户名
                    response.delete_cookie('username')
                # 返回应答
                return response
            else:
                # 用户未激活
                return render(request, 'login.html', {'errmsg':'用户名未激活,请先激活'})
        else:
            # 用户名或密码错误
            return render(request, 'login.html', {'errmsg': "用户名与密码不匹配"})


# 登出账号 /user/logout
class LogoutView(View):
    """退出登录"""
    def get(self, request):
        # django自带的认证系统功能,能登出账号
        logout(request)
        # 返回应答,转到首页
        return redirect(reverse('goods:index'))


# 用户中心视图 /user/
# class UserInfoView(View):
# class UserInfoView(LoginRequiredView, View):
class UserInfoView(LoginRequiredViewMixin, View):
    # 调用的是View里的as_view()方法,使用下面的方法查看调用父类方法时.本次程序方法的调用顺序, 当第一个父类中使用到一个该父类没有的方法时,会先到该子类的第二个父类中去
    # 寻找有没有这个方法 而不是先到第一个父类的父类去寻找
    # print(UserInfoView.__mro__)
    """用户中心信息页,需要用户名,电话,默认地址,还有浏览历史"""
    def get(self, request):
        # 获取登陆的用户,django 认证系统通过request.user可以取得登录的用户(通过session)取得,可以直接在模板中使用
        user = request.user
        # 获取用户默认地址  (address = Address.object.get(user_id=user.id, is_default=True))
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 用户不存在默认地址
        #     address = None
        # 重定义了模型管理器类对象objects(),get_default_address()方法定义在models 里的 模型管理器类
        address = Address.objects.get_default_address(user)

        # 获取用户最近的浏览记录,使用redis包里的StrictRedis()
        # 获取redis数据库的连接对象
        # 因为在settings.py中设置redis为默认缓存,也可以使用django_redis 获取redis链接 from django_reids import get_redis_connection
        #  conn = get_redis_connection('default')
        conn = StrictRedis(host='127.0.0.1', port=6379, db=6)
        # redis数据库的key,使用list数据类型,在用户中心里获取浏览记录, 当用户浏览一个商品的详情添加浏览记录,(goods应用, views模块,DeatailView)
        history_key = 'history_%d' % user.id
        # 查询数据库,获取5个最新的浏览数据,网页每次显示5个,返回列表
        sku_ids = conn.lrange(history_key, 0, 4)  # [1,2,3,4]
        # 最新数据的下标为0,所以需要重新排序,这里得到的只是商品的id号,需要找到商品的详细信息
        # 如果商品下架,可以继续显示,然后,当用户点击商品时,提示用户商品已下架
        skus = GoodsSKU.objects.filter(id__in=sku_ids)
        history_look = []
        for id in sku_ids:
            for goods in skus:
                if goods.id == int(id):
                    history_look.append(goods)
        # 组织模板上下文
        context = {
            'page': 'user_info',
            'address': address,
            'history_look': history_look
        }
        # 返回模板
        return render(request, 'user_center_info.html', context)


# 用户订单视图 /user/order/page(页码)   因为在个人中心的订单页面中, 模板文件中对订单的显示采用分页处理,所以需要接受一个页面请求参数page,一般默认是1
# 需要返回的数据有,订单创建时间, 订单编号, 每笔订单的总价, 支付款状态
# class UserOrderView(View):
# class UserOrderView(LoginRequiredView, View):
class UserOrderView(LoginRequiredViewMixin, View):
    """显示视图"""
    def get(self, request, page):
        # 获取登录用户, 可以直接在模板中使用
        user = request.user
        # 参数获取
        # 获取用户订单信息, 并根据订单的建立时间倒序排序
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')
        # 遍历的得到的查询集,得到具体订单
        for order in orders:
            # 获得订单下的商品集
            order_skus = OrderGoods.objects.filter(order=order)
            # 遍历商品集,得到具体商品, 计算每种商品的小计
            for order_sku in order_skus:
                amount = order_sku.count*order_sku.price
                # 给order_sku增加属性amount，保存订单商品的小计
                order_sku.amount = amount
            # 获取订单中处于支付状态的名称
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            # 获取订单的运费,计算实付款
            order_total_pay = order.transit_price + order.total_price
            # 给订单添加一个实付款的属性
            order.order_total_pay = order_total_pay
            # 给订单增加一个属性,代表该订单的所有商品集
            order.order_skus = order_skus

        # 进行分页, 返回一个包含信息的Paginator()对象,这里设置每页显示多少条条订单,第一个参数为数据总量
        paginator = Paginator(orders, 2)

        # 处理页码
        page = int(page)
        if page > paginator.num_pages or page < 0:
            # 显示第一页
            page = 1
        # 获取第page页的page对象
        order_page = paginator.page(page)

        # 页码处理(页面最多只显示出5个页码)
        # 1.总页数不足5页，显示所有页码
        # 2.当前页是前3页，显示1-5页
        # 3.当前页是后3页，显示后5页
        # 4.其他情况，显示当前页的前2页，当前页，当前页后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 组织末班模板上下文
        context = {
            'pages':pages,
            'order_page': order_page,
            'page': 'order'
        }
        return render(request, 'user_center_order.html', context)


# 用户收货地址视图 /user/address
# class AddressView(View):
# class AddressView(LoginRequiredView, View):
class AddressView(LoginRequiredViewMixin, View):
    """显示"""
    def get(self, request):
        # 获取登录用户
        user = request.user

        # 获取用户默认地址
        # try:
        #     address = Address.objects.get(user=user, is_default=True) # address 是一个对象,包含一整条数据
        # except Address.DoesNotExist:
        #     # 用户不存在默认地址
        #     address = None

        # 重定义了模型管理器类对象objects(),get_default_address()方法定义在models 里的 模型管理器类
        address = Address.objects.get_default_address(user)
        return render(request, 'user_center_site.html', {'page':'addr','address':address})

    # 接收地址提交
    def post(self, request):
        # 获取参数
        # 获取登录用户
        user = request.user
        print(user)
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        # 参数校验
        if not all([user, receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '请填写完整信息后,再进行提交'})

        # 业务处理: 添加收货地址
        # 如果用户的地址已经存在默认收货地址，新添加的地址作为非默认地址，否则添加的地址作为默认地址

        # 获取用户的默认地址
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 用户不存在默认地址
        #     address = None

        # 重定义了模型管理器类对象objects(),get_default_address()方法定义在models 里的 自定义的模型管理器类 AddressManager
        address = Address.objects.get_default_address(user)
        is_default = True
        if address:
            is_default = False

        # obj = Address(user=user, receiver=receiver, addr=addr, zip_code=zip_code, phone=phone, is_default=is_default)  obj.save()
        # 添加地址
        Address.objects.create(user=user,  # 外键
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)
        # 返回应答
        return redirect(reverse('user:address'))
