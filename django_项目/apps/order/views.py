from django.shortcuts import render,redirect
from django.views.generic import View
from django.http import JsonResponse
from django.core.urlresolvers import reverse
# 导入该模块进行事务处理,并设置事务保存点, 当事务失败时,回滚到事务保存点
from django.db import transaction
from django.conf import settings

from user.models import Address
from goods.models import GoodsSKU
from order.models import OrderInfo,OrderGoods

from utils.mixin import LoginRequiredViewMixin
from django_redis import get_redis_connection
from datetime import datetime
# 实现接入支付宝进行支付的第三方模块
from alipay import AliPay
import os


# /order/place
# get请求页面, post请求提交数据
# 使用getlist获取一个键下多个重复值
# 能进行此项post提交的话就说明已经登录, 所以不用进行是否登录校验
class OrderPlaceView(LoginRequiredViewMixin, View):
    """生成订单信息"""
    def post(self, request):
        """提交订单"""
        # 参数获取
        # 获取用户所需要购买的商品的id
        sku_ids = request.POST.getlist('sku_ids')
        # 参数校验
        if not all([sku_ids]):
            return redirect(reverse('cart:show'))
        # 业务处理：页面信息获取
        # 获取用户的收货地址信息
        user = request.user
        # 地址对象, 包含多个地址
        addrs = Address.objects.filter(user=user)
        # 从缓存中获取用户购物车的商品信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        skus = []
        total_count = 0
        total_price = 0
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            # 获取该种商品在购物车中的数量
            count = conn.hget(cart_key, sku_id)
            # 计算一种商品的总价格
            amount = int(count)*sku.price
            # 给sku对象增加属性count和amount, 分别保存用户所要购买的商品的数目和小计
            sku.amount = amount
            sku.count = int(count)
            # 添加商品到列表中
            skus.append(sku)
            total_count += int(count)
            total_price += amount
        # 运费, 在实际项目中, 会创建一个计算运费的子系统
        transit_price = 10
        # 实付款
        total_pay = total_price + transit_price
        # 组织上下文

        sku_ids = ','.join(sku_ids)  # 1,2,3,4,5
        context = {
            'total_count': total_count,
            'total_price': total_price,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'addrs': addrs,
            'skus': skus,
            'sku_ids': sku_ids
        }
        # 使用模板
        return render(request, 'place_order.html', context)


# 订单创建的流程:
    # 接收参数
    # 参数校验
    # 组织订单信息
    # todo: 向df_order_info表中添加一条记录
    # todo: 遍历向df_order_goods中添加记录
        # 获取商品的信息
        # 从redis中获取用户要购买商品的数量
        # todo: 向df_order_goods中添加一条记录
        # todo: 减少商品的库存，增加销量
        # todo: 累加计算用户要购买的商品的总数目和总价格
        # todo: 更新order对应记录中的total_count和total_price
        # todo: 删除购物车中对应的记录
    # 返回应答


"""悲观锁,乐观锁"""
# /order/commit
# 前端采用ajax post请求
# 传递的参数：收货地址id(addr_id) 支付方式(pay_method) 用户要购买商品id(sku_ids) 1,2,3
# 当用户提交订单后, 当需要往数据库查询,以及写入数据时,需要使用事务进行提交,一荣具荣.一损俱损,防止某一步无法顺利完成操作后,相关数据表之间数据不同步
# 并且需要使用悲观锁或乐观锁进行并发处理,解决高并发时,数据库数据不准确的问题,在使用乐观锁时,需要考虑到mysql的事务隔离级别,需要切换到Read Committed（读取提交内容）,默认是可重读模式
# 使用悲观锁方式: 在使用模型查询数据时,使用上select_for_update()方法再加上过滤器 如sku = GoodsSKU.objects.select_for_update().get()
# 冲突比较少的时候，使用乐观锁。
# 冲突比较多的时候，使用悲观锁。
"""悲观锁代码"""
class OrderCommitView(View):
    """订单提交
    """
    # 使用该模块下的一个装饰器, 进行装饰, 进行事务的设置
    @transaction.atomic
    def post(self, request):
        """订单创建"""
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})
        # 参数获取
        # "addr_id": add_id,
        # "pay_method": pay_method,
        # "sku_ids": sku_ids,
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        # 参数校验
        # 判断参数完整性
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})
        # 校验地址信息
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res':2, 'errmsg':'地址信息不存在'})
        # 校验支付方式 keys(),取出字典的的键
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res':3, 'errmsg':'支付方式不合法'})
        # 组织订单信息
        # 订单id: 20171226120020+用户id  strftime('%Y%m%d%H%M%S')  年月日时分秒 设置日期的拼接方式
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

        # 运费
        transit_price = 10

        # 总数目和总价格
        total_count = 0
        total_price = 0

        # todo: 下一步需要向数据库进行写入数据操作, 所以在这里进行设置一个事务保存点
        sid = transaction.savepoint()

        # todo: 向df_order_info表中添加一条记录
        try:
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)
            # todo: 遍历向df_order_goods中添加记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            # sku_ids 由上一个视图传给模板时已经转换成由','分隔的字符串
            sku_ids = sku_ids.split(',')
            # print('切割后')
            # print(sku_ids)
            # print(type(sku_ids))
            for sku_id in sku_ids:
                # sku_id 是str类型, ????? id?????, 为什么不转换类型也可以, 为什么
                # 获取商品信息
                try:

                    # todo:当查询商品时,加上悲观锁,因为该模型类查询集返回的对象商品里包含着库存,当前一个用户下单成功,修改了库存时再让下一个用户进行数据库查询
                    # 如果必须保证用户拿到数据，必须使用悲观锁，事务提交有时间限制，如果事务在设置好的时间内尝试提交事务
                    # 在一轮循环中，调用一次save()方法后当前事务被进行提交，如果下一轮循环中需要获取并进行上锁的数据有其他事务正在锁定
                    # 那么它就会等待，直到获得该数据，并进行上锁
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)

                except GoodsSKU.DoesNotExist:
                    # 读取失败, 返回到事务保存点
                    transaction.savepoint_rollback(sid)  # 事务保存点在142行
                    return JsonResponse({'res':4, 'errmsg':'有商品不存在系统中'})
                # 获取商品的数量
                count = conn.hget(cart_key, sku_id)
                # 在向创建订单商品表前,判断库存是否满足商品的数量
                if int(count) > sku.stock:
                    # 商品库存不足, 撤销操作,回滚到事务保存点,并返回应答
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({'res':6, 'errmsg':'库存不足!'})
                # todo: 向df_order_goods中添加一条记录
                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price)
                # todo: 减少商品的库存，增加销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()
                # todo: 累加计算用户要购买的商品的总数目和总价格
                total_count += int(count)
                total_price += sku.price*int(count)

            # todo: 更新order对应记录中的total_count和total_price
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            # 操作失败, 回滚到sid事务保存点
            transaction.savepoint_rollback(sid)  # 事务保存点在142行
            return JsonResponse({'res':7, 'errmsg':'系统正忙!下单失败,请稍后重试!'})

        # todo: 删除购物车中对应的记录 sku_ids=[1,2] *sku_ids 解包后传入
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res':5, 'msg':'订单创建成功'})


# 乐观锁添加思路: 先将向数据进行查询,添加数据的操作放进循环里,循环次数要合适
# 在更新数据库操作前一步计算理论上更改后应得数据,再使用查询集进行限制查询,
# 只有当查询出来的数据和理论数据一致,才进行更新数据,更新数据后,再向数据库中写入包含了该数据的数据表信息
# 如 res = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
# 当返回 res 为零 时代表数据更新失败,乐观锁不是真的锁
# 冲突比较少的时候，使用乐观锁。
# 冲突比较多的时候，使用悲观锁。
"""与上面上一个视图同样功能的乐观锁代码"""
# class OrderCommitView(View):
#     """订单创建"""
#     # 使用该模块下的一个装饰器, 进行装饰, 可以进行事务的设置
#     @transaction.atomic
#     def post(self, request):
#         """订单创建"""
#         # 判断用户是否登录
#         user = request.user
#         if not user.is_authenticated():
#             return JsonResponse({'res':0, 'errmsg':'用户未登录'})
#         # 参数获取
#         # "addr_id": add_id,
#         # "pay_method": pay_method,
#         # "sku_ids": sku_ids,
#         addr_id = request.POST.get('addr_id')
#         pay_method = request.POST.get('pay_method')
#         sku_ids = request.POST.get('sku_ids')
#         # print('切割前')
#         # print(sku_ids)
#         # print(type(sku_ids))
#         # 参数校验
#         # 判断参数完整性
#         if not all([addr_id, pay_method, sku_ids]):
#             return JsonResponse({'res':1, 'errmsg':'数据不完整'})
#         # 校验地址信息
#         try:
#             addr = Address.objects.get(id=addr_id)
#         except Address.DoesNotExist:
#             return JsonResponse({'res':2, 'errmsg':'地址信息不存在'})
#         # 校验支付方式 keys(),取出字典的的键
#         if pay_method not in OrderInfo.PAY_METHODS.keys():
#             return JsonResponse({'res':3, 'errmsg':'支付方式不合法'})
#         # 组织订单信息
#         # 订单id: 20171226120020+用户id  strftime('%Y%m%d%H%M%S')  年月日时分秒 设置日期的拼接方式
#         order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
#
#         # 运费
#         transit_price = 10
#
#         # 总数目和总价格
#         total_count = 0
#         total_price = 0
#
#         # todo: 下一步需要向数据库进行写入数据操作, 所以在这里进行设置一个事务保存点
#         sid = transaction.savepoint()
#
#         # todo: 向df_order_info表中添加一条记录
#         try:
#             order = OrderInfo.objects.create(order_id=order_id,
#                                              user=user,
#                                              addr=addr,
#                                              pay_method=pay_method,
#                                              total_count=total_count,
#                                              total_price=total_price,
#                                              transit_price=transit_price)
#             # todo: 遍历向df_order_goods中添加记录
#             conn = get_redis_connection('default')
#             cart_key = 'cart_%d' % user.id
#             # sku_ids 由上一个视图传给模板时已经转换成由','分隔的字符串
#             sku_ids = sku_ids.split(',')

#             for sku_id in sku_ids:
#                 # sku_id 是str类型, ????? id?????, 为什么不转换类型也可以, 为什么
#                 # 获取商品信息
#                 for i in range(5):
#                     try:
#                         sku = GoodsSKU.objects.get(id=sku_id)
#
#                     except GoodsSKU.DoesNotExist:
#                         # 读取失败, 返回到事务保存点
#                         transaction.savepoint_rollback(sid)  # 事务保存点在142行
#                         return JsonResponse({'res':4, 'errmsg':'有商品不存在系统中'})
#                     # 获取商品的数量
#                     count = conn.hget(cart_key, sku_id)
#                     # 在向创建订单商品表前,判断库存是否满足商品的数量
#                     if int(count) > sku.stock:
#                         # 商品库存不足, 撤销操作,回滚到事务保存点,并返回应答
#                         transaction.savepoint_rollback(sid)
#                         return JsonResponse({'res':6, 'errmsg':'库存不足!'})
#
#                     # todo: 减少库存,增加数量
#                     origin_stock = sku.stock
#                     new_stock = origin_stock - int(count)
#                     new_sales = sku.sales + int(count)
#                     # 先利用过滤器filter(),查询当前库存和之前取得sku对象时的库存一致,如果一致就更新库存和销量,并返回影响的行数,否则继续循环
#                     res = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
#                     if res == 0:
#                         # res为0, 数据库受到影响的行数为零,更新失败
#                         if i==4:
#                             # 尝试5次之后仍然更新失败,也就是说更新失败
#                             transaction.savepoint_rollback(sid)
#                             return JsonResponse({'res':7, 'errmsg':'系统正忙!请稍后重试!'})
#                         continue
#                     # todo: 向df_order_goods中添加一条记录
#                     OrderGoods.objects.create(order=order,
#                                               sku=sku,
#                                               count=count,
#                                               price=sku.price)
#
#                     # todo: 累加计算用户要购买的商品的总数目和总价格
#                     total_count += int(count)
#                     total_price += sku.price*int(count)
#                     # 如果在循环次数以内下单成功,就提前跳出循环
#                     break

#             # todo: 更新order对应记录中的total_count和total_price
#             order.total_count = total_count
#             order.total_price = total_price
#             order.save()
#         except Exception as e:
#             # 操作失败, 回滚到sid事务保存点
#             transaction.savepoint_rollback(sid)  # 事务保存点在142行
#             return JsonResponse({'res':7, 'errmsg':'系统正忙!下单失败,请稍后重试!'})
#
#         # todo: 删除购物车中对应的记录 sku_ids=[1,2] *sku_ids 解包后传入
#         conn.hdel(cart_key, *sku_ids)
#
#         # 返回应答
#         return JsonResponse({'res':5, 'msg':'订单创建成功'})


# /Order/pay_order
# 前端采用ajax post请求
# 传递的参数： 订单id(order_id)
class OrderPayView(View):
    """订单支付"""
    def post(self, request):
        """订单支付"""
        # 用户登录校验
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 参数校验
        if not all([order_id]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})

        # 检验订单
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res':2, 'errmsg':'订单信息错误'})

        # 业务处理
        # 初始化设置,返回一个对象,用这个对象,可以使用这个对象的方法与alipay进行交互
        alipay = AliPay(
            appid = '2016082100306860',  # 应用APPID 在alipay创建应用获取
            app_notify_url=None, # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),  # 网站私钥文件的路径
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'), # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2 签名算法类型,alipay需要通过签名进行确认身份
            debug=True  # 默认False False 表示真实的环境, True 表示沙箱环境
        )

        # 调用接口函数, 和alipay进行交互 注意必填参数, 返回的是一串可以通过地址栏传递的信息
        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        # 沙箱环境下需要跳转到 https://openapi.alipaydev.com/gateway.do? + order_string
        # 调用alipay相关接口的名字规则 把alipay相关接口的名字的点换成 '_' 然后在最开头加上'api'
        # 如 alipay.trade.page.py 在python与alipay接口交互的第三方包里的方法名字就是api_alipay__trade_page_py() 这些方法是在初始化返回的alipay对象里
        total_amount = order.total_price + order.transit_price  #  属于decimal格式数据, 无法转换成json 所以需要强制转换成str类型
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 订单id 业务参数 必传
            total_amount=str(total_amount),  # 订单总金额 业务参数 必传
            subject='天天生鲜%s' % order_id,  # 订单标题 业务参数 必传 显示支付宝付款页面
            return_url=None,  # 公共参数 可选, 填写None则表示不用alipay返回订单结果
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答
        pay_url = "https://openapi.alipaydev.com/gateway.do?" + order_string
        return JsonResponse({'res':3, 'pay_url':pay_url})


# 当前端执行支付操作后,会进行一个查询付款结果的请求
# /order/check
# 采用ajax post 进行请求
# 传递的参数为订单号 order_id
class CheckPayView(View):
    """支付结果查询"""
    def post(self, request):
        print('接收到请求')
        """支付结果查询"""
        # 登录检验
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})
        # 参数获取
        order_id = request.POST.get('order_id')

        # 参数校验
        if not all([order_id]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})

        # 校验订单id
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1
                                          )
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res':2, 'errmsg':'订单信息错误'})

        # 业务处理, 调用支付宝交易查询接口
        # 初始化, 返回对象,可以通过该对象调用方法
        alipay = AliPay(
            appid='2016082100306860',  # 应用APPID 在alipay创建应用获取
            app_notify_url=None,  # 默认回调url，设置了回调接口接口以后，支付宝会把操作结果发送到这个地址，需要进行接收
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),  # 网站私钥文件的路径
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2 签名算法类型,alipay需要通过签名进行确认身份
            debug=True  # 默认False False 表示真实的环境, True 表示沙箱环境
        )
        # 调用支付宝查询的api函数
        # 调用api函数后,alipay会返回应答, 封装在一个对象里, 里面包含了一下参数

        # {
        #         "trade_no": "2017032121001004070200176844", # 支付宝交易号
        #         "code": "10000", # 网关的返回码
        #         "invoice_amount": "20.00",
        #         "open_id": "20880072506750308812798160715407",
        #         "fund_bill_list": [
        #             {
        #                 "amount": "20.00",
        #                 "fund_channel": "ALIPAYACCOUNT"
        #             }
        #         ],
        #         "buyer_logon_id": "csq***@sandbox.com",
        #         "send_pay_date": "2017-03-21 13:29:17",
        #         "receipt_amount": "20.00",
        #         "out_trade_no": "out_trade_no15", # 网站订单号
        #         "buyer_pay_amount": "20.00",
        #         "buyer_user_id": "2088102169481075",
        #         "msg": "Success",
        #         "point_amount": "0.00",
        #         "trade_status": "TRADE_SUCCESS", # 支付交易状态
        #         "total_amount": "20.00"
        # }

        # 将查询代码放在循环里,因为在html模板里,进行了支付请求后,就立马进行了查询请求,订单尚未创建成功
        # 在这里进行循环查询,放alipay返回成功应答后,在跳出循环, 再将结果返回给用户
        # 如果订单创建失败也跳出循环
        while True:
            # 查询订单支付完成情况,只需要传递一个参数,可以是支付订单号(alipay生成),也可以是网站的订单号(在提交付款请求时已经提交到alipay)
            response = alipay.api_alipay_trade_query(out_trade_no=order_id)
            # 获取网关返回码, 不同的网管返回码,表示了查询订单的结果
            code = response.get('code')
            # 网关返回码为10000 查询到了支付订单
            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 用户支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 更新订单状态,填写支付宝交易号
                order.order_status = 4  # 待评价
                order.trade_no = trade_no # 填写支付单号
                order.save()

                # 返回应答
                return JsonResponse({'res':3, 'msg':'支付成功'})
            # 如果返回的网关为40004 则说明查询不到该订单, 支付定单也许正在创建中, 休眠一段时间后再次进行查询
            #  如果为10000, 但是支付状态为待支付也可以等待一段时间后继续进行查询
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                import time
                # 休眠5秒,继续查询,这里有个优化的思路，在前几次循环中，休眠时间可以设置长一点，然后将休眠时间设置得短一点，这符合实际实际业务场景，用户支付款成功需要时间
                time.sleep(5)
                continue

            # 如果都不是这两种情况,就说明支付款失败
            else:
                return JsonResponse({'res':4, 'errmsg':'支付失败'})


# 订单评价页面
# /order/comment/order_id
class OrderCommentView(LoginRequiredViewMixin, View):
    """订单评价"""
    def get(self, request, order_id):
        """页面显示"""
        # 参数获取
        # 获取登录用户, 可以直接在模板中使用
        user = request.user
        # 参数获取
        # 获取订单信息
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            # 当路径匹配中使用了分组的并且命名的参数, 就应该使用 kwargs = {} 字典中写上分组的名字(键)和值
            return redirect(reverse('user:order', kwargs={'page': 1}))

        # 获取订单的支付状态名称
        order_status_name = OrderInfo.ORDER_STATUS[order.order_status]
        # 获得订单下的商品集
        order_skus = OrderGoods.objects.filter(order=order)
        # 遍历商品集,得到具体商品, 计算每种商品的小计
        for order_sku in order_skus:
            amount = order_sku.count*order_sku.price
            # 给order_sku增加属性amount，保存订单商品的小计
            order_sku.amount = amount
        order_total_pay = order.transit_price + order.total_price
        # 给订单添加一个实付款的属性
        order.order_total_pay = order_total_pay
        # 给订单增加一个属性,代表该订单的所有商品集
        order.order_skus = order_skus

        # 组织模板
        context = {
            'order': order
        }
        return render(request, 'order_comment.html', context)

    # 接收评价内容的提交
    # 因为在模板中进行form 提交时,只定义了提交方式, 没有定义提交路径, 所以会提交到原来的页面
    def post(self, request, order_id):
        """提交评价内容"""
        user = request.user
        # 获取评论商品的信息
        try:
            order = OrderInfo.objects.get(order_id=order_id)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order', kwargs={'page': 1}))
        # 获取订单的商品的数目
        count = request.POST.get('count')
        try:
            count = int(count)
        except Exception as e:
            return redirect(reverse('user:order', kwargs={'page': 1}))
        # 遍历获取商品的评论信息
        for i in range(1, count+1):
            # 获取第i件商品的id
            sku_id = request.POST.get('sku_%d'%i)
            # 获取商品的信息
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except Exception as e:
                # 没有该种商品, 不能进行评论
                continue

            # 获取订单商品的信息
            try:
                order_sku = OrderGoods.objects.get(order=order, sku=sku)
            except Exception as e:
                # 用户没有购买过该商品, 不能进行评论
                continue

            # 获取对应的商品的评论内容
            comment = request.POST.get('content_%d'%i)

            # 设置单件商品的评论
            order_sku.comment = comment
            order_sku.save()

        # 更新订单的状态
        order.order_status = 5
        order.save()

        # 返回应答, 跳转到用户订单页面
        return redirect(reverse('user:order', kwargs={'page':1}))

