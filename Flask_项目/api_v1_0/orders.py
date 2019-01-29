# coding=utf8

from datetime import datetime

from flask import request, current_app, jsonify, g

from ihome import db
from ihome.api_v1_0 import api
from ihome.models import User, House, Order
from ihome.utils.common_dicorator import login_required
from ihome.utils.response_code import RET
from ihome import redis_store

# 用户进行下单
# post /order
@api.route('/order', methods=['POST'])
@login_required
def make_order():
    """用户进行下单操作"""
    # 下单操作应该使用悲观锁或者乐观锁 保证高并发情况下数据的一致性
    # 获取参数, 用户id, 房屋id, 入住时间, 和截止时间
    # 校验参数完整性,
    # 检验参数合法性, 用户可以向自己的提供的房源下订单
    # 生成订单, 向数据库中写入数据
    # 下单成功, 返回应答
    user_id = g.user_id
    # 获取参数
    req_dict = request.get_json() # 返回的是字典
    house_id = req_dict.get('house_id')
    start_date_str = req_dict.get('start_date')
    end_date_str = req_dict.get('end_date')
    # 校验参数完整性
    if not all([house_id, start_date_str, end_date_str]):
        return jsonify(errcode=RET.PARAMERR, errmsg='参数错误')
    # 判断房屋是否存在
    try:
        house = House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.PARAMERR, errmsg='房源不存在')
    # 判断日期格式是否合法
    try:
        start_date_time = datetime.strptime(start_date_str, "%Y-%m-%d")  # 将字符串类型, 按照格式转换为时间类型
        end_date_time = datetime.strptime(end_date_str, "%Y-%m-%d")
        # 断言, 如果为真, 则继续执行程序, 为假则不再执行程序, 抛出异常
        assert end_date_time >= start_date_time
        # 日期类型支持加减操作
        days = (end_date_time - start_date_time).days + 1  # 两个日期数据相加减, 返回相差的天数 通过其days属性可以得到整型数据
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.PARAMERR, errmsg="日期格式错误, 请确认!")

    # 判断房屋是否是用户房屋, 防止用户向自己的房屋下单, 防止刷单
    if user_id == House.user_id:
        return jsonify(errcode=RET.REQERR, errmsg='禁止刷单')

    # 判断该house有无其他用户在该时间段内下单
    try:
        order_obj_count = Order.query.filter(Order.house_id == house_id, Order.end_date >= start_date_time,
                                            Order.begin_date <= end_date_time).count()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='数据库异常')
    if order_obj_count > 0:
        return jsonify(errcode=RET.DATAEXIST, errmsg="房屋该时间内存在冲突订单, 请更改!!!")

    # 下订单, 编辑订单数据
    order = Order(
        user_id=user_id,
        house_id=house_id,
        begin_date=start_date_time,
        end_date=end_date_time,
        days=days,
        house_price=house.price,
        amount=(house.price * days)
    )
    # 更新数据库数据, 生成订单
    try:
        db.session.add(order)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errcode=RET.DBERR, errmsg='数据异常, 请稍后重试')

    # 返回订单号给用户
    return jsonify(errcode=RET.OK, errmsg="OK", data={'order_id':order.id})


# 用户查询订单
# get /uesr/order/
@api.route('/user/order', methods=['GET'])
@login_required
def user_order_info():
    """用户查询订单信息"""
    user_id = g.user_id
    # 用户的身份，用户想要查询作为房客预订别人房子的订单，还是想要作为房东查询别人预订自己房子的订单
    role = request.args.get("role")
    # 查询订单数据
    try:
        if "landlord" == role:
            # 以房东的身份查询订单
            # 先查询属于自己的房子有哪些
            houses = House.query.filter(House.user_id==user_id).all()
            house_ids = [house.id for house in houses]
            # 查询预定了自己房子的订单
            orders = Order.query.filter(Order.house_id.in_(house_ids)).order_by(Order.create_time.desc()).all()
        else:
            # 以房客身份查看自己下了什么订单
            orders = Order.query.filter(Order.user_id==user_id).order_by(Order.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='查询订单信息失败')
    # 将订单信息转化为字典数据
    order_dict_list = []
    for order in orders:
        orders = order_dict_list.append(order.to_dict())
    return jsonify(errcode=RET.OK, errmsg='OK', data={"order":orders})


@api.route('/order/<int:order_id>/status', methods=['PUT'])
@login_required
def accept_or_refuse_order(order_id):
    """房东接单或拒单"""
    user_id = g.user_id
    # 获取参数
    req_dict = request.get_json()
    action = req_dict.get('action')
    if not action:
        return jsonify(errcode=RET.PARAMERR, errmsg='参数缺失')
    status = req_dict.get("action")
    if status not in ('accept', 'refuse'):
        return jsonify(errcode=RET.PARAMERR, errmsg='参数错误')
    # 查询订单, 确认订单状态是否处于待接单状态
    try:
        order = Order.query.get(order_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errrmsg='数据库异常')
    else:
        if not order:
            return jsonify(errcode=RET.NODATA, errmsg='查询不到订单')
    if order.status != "WAIT_ACCEPT":
        return jsonify(errcode=RET.NODATA, errmsg='订单不在待处理状态')
    # 确保房东只能修改属于自己的房子订单
    house = order.house_id
    if house.id != user_id:
        return jsonify(errcode=RET.PARAMERR, errmsg='操作无效')
    # 接单
    if action == 'accept':
        # 接单, 将订单状态设置为等待评论
        order.status = 'WAIT_COMMENT'
    elif action == 'refuse':
        # 拒单, 要求用户传递拒单的原因
        reason = req_dict.get('reason')
        if not reason:
            return jsonify(errcode=RET.PARAMERR, errmsg="请填写拒单原因")
        order.status = "REJECTED"
        order.comment = reason
    # 向数据库提交修改
    try:
        db.session.add(order)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errcode=RET.DBERR, errmsg='数据错误')
    return jsonify(errcode=RET.OK, errmsg='OK')


@api.route("/order/<int:order_id>/comment", methods=['PUT'])
@login_required
def change_comment(order_id):
    """用户提交订单评论"""
    user_id = g.user_id
    # 参数获取
    req_dict = request.get_json()
    comment = req_dict.get('comment')
    # 校验参数的合法性
    try:
        # 需要确保只能评论自己下的订单，而且订单处于待评价状态才可以
        order = Order.query.filter(Order.id==order_id, Order.user_id==user_id, Order.status=="WAIT_COMMENT").first()
        house = order.house
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg="数据库错误")
    if not order:
        return jsonify(errcode=RET.REQERR, errmsg='操作无效')
    try:
        order.status = "COMPLETE"
        order.comment = comment
        house.order_count += 1
        db.session.add(order)
        db.session.add(house)
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errcode=RET.DBERR, errmsg='数据库错误')
    # 因为房屋详情中有订单的评价信息，为了让最新的评价信息展示在房屋详情中，所以删除redis中关于本订单房屋的详情缓存
    try:
        redis_store.delete("house_info_%s" % order.house_id)
    except Exception as e:
        current_app.logger.error(e)
    return jsonify(errcode=RET.OK, errmsg='OK')
