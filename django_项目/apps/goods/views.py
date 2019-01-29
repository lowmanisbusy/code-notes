from django.shortcuts import render, redirect
from django.views.generic import View
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, GoodsSKU
from order.models import OrderGoods
from django_redis import get_redis_connection

# 使用该模块的方法, 可以设置和取出缓存(缓存一些无须用户登录就可以获取的数据)
# 保存缓存的载体已经在settings中设置成redis
from django.core.cache import cache

from django.core.urlresolvers import reverse
from django.core.paginator import Paginator

# http://127.0.0.1:8000/index
class IndexView(View):
    """首页"""
    def get(self, request):
        """显示网页"""
        # 每次来自浏览器首页的请求,都先尝试获取缓存
        context = cache.get('index_page_data')

        if context is None:
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

            # 将购物车显示数量设置为零
            cart_count = 0

            # 组织缓存的上下文
            context = {
                'types': types,
                'index_banner': index_banner,
                'promotion_banner': promotion_banner,
                'cart_count': cart_count
            }
            # 设置缓存, 第一个参数是键名,第二个值,第三个是过期时间, 不设置过期时间,就是永不过期
            cache.set('index_page_data', context, 3600)
            print("进入设置缓存函数")
        # 获取登录用户后购物车商品的数目,先设置为零
        cart_count = 0
        # 获取user
        user = request.user
        if user.is_authenticated():
            # 用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)
        # 更新模板上下文
        context.update(cart_count=cart_count)
        # 使用模板
        return render(request, 'index.html', context)


# 访问商品的详情页面时候，需要传递商品的id
# 前端向后端传递参数的方式:
# 1. get（只涉及到数据的获取) /goods?sku_id=商品id
# 2. post(涉及到数据的修改) 传递
# 3. url捕获参数 /goods/商品id
class DetailView(View):
    """详情页"""
    # 在url中进行了分组,需要拿回参数
    def get(self, request, sku_id):
        """显示商品详情页"""
        # 获取参数, 捕捉错误, 因为用户有可能输入的数据在数据库没有匹配项
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在, 跳转到首页
            return redirect(reverse('goods:index'))
        # 获取商品的分类信息
        types = GoodsType.objects.all()

        # 获取和商品同一分类的新品的信息,老师的这个方法,要查询出所有的数据,是不是效率太差了
        # new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        # 可以使用objects里的raw()方法, 然后直接填写SQL语句进行数据库查询 books = bookinfo.objects.raw("SQL语句")
        info_id = sku.type.id
        # 只从数据库查出最新的2个数据
        new_skus = GoodsSKU.objects.raw("select * from df_goods_sku where type_id = %d order by id desc limit 2;" % info_id)

        # 获取商品的评论信息, exclude() 取反
        order_skus = OrderGoods.objects.filter(sku=sku).exclude(comment='').order_by('-update_time')

        # 获取和sku商品同一SPU的其他规格的商品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=sku_id)
        cart_count = 0
        user = request.user
        if user.is_authenticated():
            # 获取用户的购物车条目数
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

            # 添加用户的浏览历史记录
            history_key = 'history_%d' % user.id
            # 先从redis里删除以往浏览该商品的信息
            conn.lrem(history_key, 0, sku_id)
            # 把最新的浏览信息添加进去
            conn.lpush(history_key, sku_id)
            # 保留用户最近浏览的5个商品的id
            conn.ltrim(history_key, 0, 4)
            # 组织模板上下文
        context = {
            'types': types,
            'sku':sku,
            'new_skus': new_skus,
            'comment' : order_skus,
            'same_spu_skus' : same_spu_skus,
            'cart_count': cart_count,
            "order_skus":order_skus
        }

        # 返回应答
        return render(request, 'detail.html', context)


# 访问列表页面的时候，需要传递的参数
# 种类id(type_id) 页码(page) 排序方式(sort)
# /list?type_id=种类id&page=页码&sort=排序方式
# /list/种类id/页码/排序方式
# /list/种类id/页码?sort=排序方式
# /list/7/1/?sort=排序方式参数
class ListView(View):
    """列表页面"""
    def get(self, request, type_id, page):
        """显示"""
        # 获取参数
        print(type_id)
        print(page)
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            # 商品种类不存在，跳转到首页
            return redirect(reverse('goods:index'))

        # 获取商品分类信息
        types = GoodsType.objects.all()

        # 获取用户请求的排序方式, 排序方式,是通过get请求的方式进行请求的
        # sort=='default':按照默认方式(商品id)排序
        # sort=='price':按照商品的价格(price)排序
        # sort=='hot':按照商品的销量(sales)排序
        # < a href = { % url'goods:list' type.id 1 %}?sort = defalult { % if sort == 'default' %} class ="active" {% endif %} > 默认 < / a >

        sort = request.GET.get('sort', 'default')  # 如果没有传参就使用默认值'default'
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')
        # 使用django 的Paginator()将所得数据进行分页 第一个为数据总量, 第二个为每页显示的数据量, 这里设置为1个
        # 返回一个包含所有页面的对象,使用这个实例对象,可以使用里面的方法及属性
        paginator = Paginator(skus, 1)

        # 处理请求的页码
        page = int(page)
        # num_pages 属性,页面总数
        if page > paginator.num_pages or page<=0:
            page = 1
        # 获取用户请求的当前页的Page对象(第page页), 包含当前页的所有sku
        skus_page = paginator.page(page)

        # 页码处理(页面最多只显示出5个页码)
        # 1.总页数不足5页，显示所有页码
        # 2.当前页是前3页，显示1-5页
        # 3.当前页是后3页，显示后5页
        # 4.其他情况，显示当前页的前2页，当前页，当前页后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)
        elif page < 4:
            pages = range(1, 6)
        elif page > (num_pages-3):
            pages = range(num_pages-4, num_pages+1)
        else:
            pages = range(page-2, page+3)

        # 获取该分类下的2个新品信息
        info_id = type.id
        new_skus = GoodsSKU.objects.raw("select * from df_goods_sku where type_id = %d order by id desc limit 2;" % info_id)

        # 获取用户购车中的商品的条目数
        cart_count = 0
        # 获取user
        user = request.user
        if user.is_authenticated():
            # 用户已登录
            # 获取登录用户购物车中商品的条目数,使用哈希数据格式
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context = {'types': types,
                   'type': type,
                   'skus_page': skus_page,
                   'pages':pages,
                   'new_skus': new_skus,
                   'cart_count': cart_count,
                   'sort':sort}
        # 使用模板
        return render(request, 'list.html', context)
