from django.conf import settings
from django.core.mail import send_mail
from django.template import loader
# 导入celery类
from celery import Celery

# 另外一台主机上启动worker时,需要初始化django所依赖的环境,打开这几行代码
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "daily_fresh.settings")
django.setup()
# celery worker启动的一端导入模型类必须在django.setup()之后
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner


# 创建一个Celery类的对象,第一个参数是名称,第二个指向中间人,这里使用redis,指定那个数据库,需先启动redis数据库服务器
app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/5')


#  定义任务函数,使用创建出来的celery类对象的task方法作为一个装饰器  ? 为什么
@app.task
def send_register_active_email(email, username, token):
    # 组织发送内容
    # 邮件标题
    subject = '天天生鲜欢迎您'
    # 邮件正文,此处设置为空
    message = ''
    # 邮件发送方
    sender = settings.EMAIL_FROM
    # 邮件接收方,将所有接收方存放在一个列表里
    receiver = [email]
    # 要发送的链接
    send_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击以下链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (
        username, token, token)
    # 发送邮件,将message 赋值给html_message 可以将内容在客户端以html文本显示
    send_mail(subject, message, sender, receiver, html_message=send_message)

    # 去到celery_tasks文件夹所在目录下, 工作者可以不再同一个主机下, 但是需要将这个文件下的代码复制到运行工作者主机上
    # 启动中间人,这里使用redis服务器
    # 进入安装了redis 和 celery 的虚拟环境 运行工作者
    # 输入命令 celery -A celery_tasks.tasks worker -l info  命令不要写错
    # 运行工作者, 后面两个参数的意思按级别显示运行的相关的信息 第三个参数就是设置的任务名称创建celery类时对应的名字


# 创建任务函数
@app.task
def generate_static_index_html():
    """生成一个静态文件, 因为生成静态文件属于耗时操作,如果在视图中操作将会影响程序性能,所以使用celery"""

    # 获取商品分类信息, 有那几大类商品
    types = GoodsType.objects.all()

    # 获取首页轮播商品的信息
    index_banner = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销活动的信息
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品活动的信息
    # types_goods_banner = IndexTypeGoodsBanner.objects.all()

    for type in types:
        # 根据type查询type种类首页展示的文字商品信息和图片商品信息
        title_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
        image_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 给type对象增加两个属性title_banner, image_banner
        # 分别保存type种类首页展示的文字商品信息和图片商品信息
        type.title_banner = title_banner
        type.image_banner = image_banner

    # 购物车商品的数目用户登录前显示为零
    cart_count = 0

    # 组织模板上下文, 因为需要生成静态网页, 所有与用户登录后有关的数据都不须要获取
    context = {
        'types': types,
        'index_banner': index_banner,
        'promotion_banner': promotion_banner,
        'cart_count': cart_count,
    }

    # 渲染产生静态首页的html内容
    # 1.加载模板, 获取模板对象, 在模板中定义了static_base.html static_index.html两个模板
    temp = loader.get_template('static_index.html') # 导入包, 使用该模块的方法
    # 2.模板渲染,产生替换后的html内容使用上一步产生的模板对象里的render()方法,会将参数传递给模板,并并返回模板对象
    static_html = temp.render(context)

    # 创建一个静态首页文件
    # 指定路径
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_html)
    print('生成完成')
    # 可以通过访问nginx的域名直接访问静态首页(需要将整份项目代码复制到nginx主机上(如果nginx在另外一台主机上))
    # 然后修改这个文件 /usr/local/nginx/conf$  sudo vi nginx.conf  修改成以下内容, (那么问题来了,如果在主机不同如何同步两份代码)
    # '''server {
    #     # 监听
    #     listen  80;
    #     server_name  localhost;
    #     # 定义静态文件的路径
    #     location /static {
    #         alias /home/python/Desktop/DailyFresh/daily_fresh/static/;
    #     }
    #     # 定义模板路径
    #     location / {
    #         root   /home/python/Desktop/DailyFresh/daily_fresh/static;
    #         index  index.html;
    #     }'''
