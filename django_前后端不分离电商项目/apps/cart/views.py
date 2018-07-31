from django.shortcuts import render, redirect
from django.views.generic import View
from django.http import JsonResponse
from django.core.urlresolvers import reverse

from goods.models import GoodsSKU

from django_redis import get_redis_connection
from utils.mixin import LoginRequiredViewMixin


# 当用户点击添加商品进购物车时,使用ajax进行传递,
# /cart/add
class CartAddView(View):
    """购物车, 使用的post请求模式, 有数据修改使用post请求方式"""
    def post(self, request):
        """记录添加"""
        # 获取参数
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})
        # 关于购物车的添加前端只需要传递 商品ID以及添加的数量
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 参数校验
        if not all([sku_id, count]):
            return JsonResponse({'res':1, 'errmsg':'请选择需要添加的商品及数量'})

        # 校验商品的id
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res':2, 'errmsg':'该商品不存在'})
        # 校验用户传递过来的商品数量是否合法
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res':3, 'errmsg':'请输入正确的商品数量'})
        if count <= 0:
            return JsonResponse({'res':3, 'errmsg':'请输入正确的商品数量'})
        # 业务处理,购物车记录添加 使用redis数据库进行储存 使用的数据格式是hash
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 先尝试从cart_key对应的hash元素中获取属性sku_id的值, 有相同的商品就进行添加, 查询出来的是sku_id 商品的件数
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            # 用户购车中已经添加过该商品，数目需要累加, 因为redis中,所有的元素都是str,所以需要进行转化
            count += int(cart_count)

        # 判断商品的库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 设置用户购物车中商品的数目
        conn.hset(cart_key, sku_id, count)
        # 获取购物车商品种类的数目
        type_count = conn.hlen(cart_key)
        # 返回应答
        return JsonResponse({'res':5, 'type_count': type_count, 'msg':'添加商品成功'})


# 显示购车页面 /cart/show
#  需要提供的参数 购物车记录 hget(cart_key, sku_id) redis数据库 用户需登录 get请求页面, 修改数据使用post请求
class CartInfoView(LoginRequiredViewMixin, View):
    """购物车页面"""
    def get(self, request):
        """显示"""
        # 参数获取
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated():
           return  redirect(reverse('user:register'))
        # 只需要获得用户的id值
        cart_key = "cart_%d" % user.id
        # 建立与redis的链接
        conn = get_redis_connection('default')
        # 获取用户的购物车记录
        cart_dict = conn.hgetall(cart_key)  # {'商品id':商品数量} hgetall()获取某个键的所有属性和值,返回的是一个字典

        skus = []
        total_count = 0
        total_price = 0
        # 遍历 cart_dict
        for sku_id, count in cart_dict.items():
            # 根据商品获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)

            # 单种商品的总价
            amount = sku.price*int(count)
            # 给sku增加属性count, amount,分别保存用户购物车中添加的商品的数目和商品的小计
            sku.count = int(count)
            sku.amount = amount
            # 计算商品的总价
            total_price += amount
            # 计算商品的总数量
            total_count += int(count)
            skus.append(sku)
        # 组织参数
        context = {
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price
        }

        # 返回应答
        return render(request, 'cart.html', context)


# 使用的是ajax请求
# 传递的参数包括 sku_id, count
# /cart/update
class CartUpdateView(View):
    """购物车记录的跟新"""
    def post(self, request):
        print('接收到请求')
        """更新"""
        # 确认用户是否登录
        user = request.user

        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'请先登录账号!'})

        # 参数获取
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 参数校验
        if not all([sku_id, count]):
            return JsonResponse({'res':1, 'errmsg': '请输入完整数据'})

        # 校验商品的id
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist as e:
            return JsonResponse({'res':2, 'errmsg':'系统无该商品'})

        # 校验商品的数目
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': '商品数目须为正整数'})
        if count <= 0:
            # 商品数目非法
            return JsonResponse({'res': 3, 'errmsg': '商品数目须为正整数'})
        # 业务处理
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        # 判断商品的库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})
        # 更新购物车的记录
        conn.hset(cart_key, sku_id, count)

        # 计算用户购物车中的商品的总件数 在redis 中, hvals() 返回哈希表 key 中所有域的值。
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count = int(val)
        print('更新成功')
        return JsonResponse({'res':5, 'total_count':total_count, 'msg':'更新成功'})


# 使用json进行请求 POST请求方式
# 需要传递的参数 sku_id
# /cart/delete
class CartDeleteView(View):
    """删除购物车记录"""
    def post(self, request):
        """购物车记录的更新"""
        # 获取参数
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'请先进行登录'})
        # 获取商品id
        sku_id = request.POST.get('sku_id')
        if not all([sku_id]):
            return JsonResponse({'res':1, 'errmsg': '请选择需要删除的商品'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 校验商品的id
        try:
            sku = conn.hget(cart_key, sku_id)
        except Exception as e:
            return JsonResponse({'res':2, 'errmsg':'购物车没有该商品'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist as e:
            return JsonResponse({'res':2, 'errmsg':'系统没有该种商品'})

        # 业务处理,删除购物车记录
        conn.hdel(cart_key, sku_id)

        # 计算用户购物车中商品的件数
        total_count = 0
        # 计算用户购物车中的商品的总件数 在redis 中, hvals() 返回哈希表 key 中所有域的值 返回的是一个大列表嵌套多个列表, 小列表里储存的值就是每种商品的个数,先遍历出来,再相加
        vals = conn.hvals(cart_key)
        # print(vals)
        for val in vals:
            total_count += int(val)
        # 返回应答
        return JsonResponse({'res': 3, 'total_count': total_count, 'message': '删除成功'})
