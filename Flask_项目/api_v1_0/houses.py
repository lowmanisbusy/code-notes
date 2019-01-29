# coding=utf8

# 导包 先写python 官方包, 再到第三方包, 然后自己的包
from datetime import datetime

from flask import current_app, jsonify, json, request, g
from flask import session

from ihome.api_v1_0 import api
from ihome.models import Area, House, Facility, HouseImage, User, Order
from ihome.utils.response_code import RET
from ihome import redis_store, constant, db
from ihome.utils.common_dicorator import login_required
from ihome.utils.qi_niu_storage import storage_image


# GET /area_info  post
# 搜索
@api.route('/area_info', methods=['GET'])
def get_area_info():
    """获取城区信息"""
    # 先尝试从redis中获取数据, 如果redis有数据, 直接返回,如果没有就从数据库获取
    # 并将数据保存到redis, 必须设置一个有效期, 以防数据过时,与mysql数据库数据不一致
    try:
        # 因为保存的是已经转化成了json格式的数据, 所以取出的也是json格式的数据, json数据,整体就是一个字符串
        resp_json_str = redis_store.get('area_info')
    except Exception as e:
        current_app.logger.error(e)
    else:
        if resp_json_str is not None:
            # 击中缓存
            current_app.logger.info('hit redis area info')
            return resp_json_str, 200, {'content-   Type':'application/json'}

    # 如果没有直接从数据查询
    try:
        # 如果没有数据就返回空列表
        areas = Area.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET, errmsg='数据库异常')

    # 获取到数据, 遍历返回值，将列表中的对象转换为字典
    areas_dict_list = []
    for area in areas:
        areas_dict_list.append(area.to_dict())  # to_dict 这个方法定义在模型类Area 里, 在这个方法里, 将具体对象的类属性取到后, 将所有取到的值重新封装成一个字典
    # 将所有需要返回的信息封装成一个字典, 将一连串参数封装成字典的前提是所有参数都是命名参数
    resp_dict = dict(errcode=RET.OK, errmsg='查询成功', data={'area':areas_dict_list})
    # 将字典转化为json数据, 先将数据转化为字典,才能使用dumps()方法
    resp_json_str = json.dumps(resp_dict)

    # 将数据保存到缓存中 redis中  字符串
    # '{"errcode":"0", "errmsg":"查询成功", "data":{"areas":[{"aid":1, "aname": "xxx"}, {}, {}]}}'
    try:
        redis_store.setex('area_info', constant.AREA_INFO_REDIS_CACHE_EXPIRES, resp_json_str)
    except Exception as e:
        current_app.logger.error(e)

    # 向前端返回数据, json '{"errcode":"0", "errmsg":"查询成功", "data":{"areas":[{"aid":1, "aname": "xxx"}, {}, {}]}}'
    # 不必再使用jsonify()方法再进行转化操作, 耗时, 但是需要手动返回部分必须的数据
    return resp_json_str, 200, {"content-Type":"application/json"}


# 用户发布房源信息
@api.route('/house/info', methods=['POST'])
@login_required
def save_house_info():
    """保存房屋信息
    前端发送过来的json数据包含以下键值
    {
        "title":"",
        "price":"",
        "area_id":"1",
        "address":"   ",
        "room_count":"",
        "acreage":"",
        "unit":"",
        "capacity":"",
        "beds":"",
        "deposit":"",
        "min_days":"",
        "max_days":"",
        "facility":["7","8"]
    }
    """
    # 获取参数
    user_id = g.user_id
    house_data = request.get_json()  # 返回的是字典
    if house_data is None:
        return jsonify(errcode=RET.PARAMERR, errmsg='参数缺失')

    title = house_data.get("title")  # 房屋名称标题
    price = house_data.get("price")  # 房屋单价
    area_id = house_data.get("area_id")  # 房屋所属城区的编号
    address = house_data.get("address")  # 房屋地址
    room_count = house_data.get("room_count")  # 房屋包含的房间数目
    acreage = house_data.get("acreage")  # 房屋面积
    unit = house_data.get("unit")  # 房屋布局（几室几厅)
    capacity = house_data.get("capacity")  # 房屋容纳人数
    beds = house_data.get("beds")  # 房屋卧床数目
    deposit = house_data.get("deposit")  # 押金
    min_days = house_data.get("min_days")  # 最小入住天数
    max_days = house_data.get("max_days")  # 最大入住天数

    # 参数校验
    if not all([title, price, area_id, address, room_count, acreage, unit, capacity, beds, deposit, min_days, max_days]):
        return jsonify(errcode=RET.PARAMERR, errmsg="参数不完整")

    # 判断数据合法性
    # 判断城区信息是否存在
    try:
        area = Area.query.get(area_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errocde=RET.DBERR, errmsg='数据库异常')
    if area is None:
        return jsonify(errcode=RET.NODATA, errmsg='城区信息错误')
    # 处理金钱数据
    try:
        price = int(float(price)*100) # 数据库中以分为单位
        deposit = int(float(deposit)*100)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.PARAMERR, errmsg='金钱格式有误')

        # 保存数据到数据库中
    house = House(
        user_id=user_id,
        area_id=area_id,
        title=title,
        price=price,
        address=address,
        room_count=room_count,
        acreage=acreage,
        unit=unit,
        capacity=capacity,
        beds=beds,
        deposit=deposit,
        min_days=min_days,
        max_days=max_days
    )
    # 处理房屋的设施信息, 因为房屋信息不是必传的, 但是当用户传递了该参数时,需要校验这些参数是否都存在于数据库中
    facilities_id_list = house_data.get('facility')  # 前端传过来的是一个列表
    if facilities_id_list:
        # 表示用户勾选了设施
        # 过滤这些设施编号，去除掉数据库中不存在的设施
        # facility_id_list -> ["1", "2", "7", "8", "100", "10000"]
        # select * from ih_facility_info where id in ("1", "2", "7", "8", "100", "10000")
        try:
            facility_obj_list = Facility.query.filter(Facility.id.in_(facilities_id_list)).all()  # 使用filter() 及in_() 方法
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errcode=RET.DBERR, errmsg='数据库异常')

    # 保存数据到数据库中
    try:
        db.session.add(house)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errcode=RET.DBERR, errmsg='数据库异常, 保存失败')
    return jsonify(errcode=RET.OK, errmsg='上传成功', data={'house_id':house.id})


# 用户上传房屋图片, 使用多媒体表单上传
@api.route('/house/images', methods=['POST'])
@login_required
def save_house_image():
    """保存用户上传的房屋图片"""
    # 获取用户id, 房屋图片, house_id
    # 参数完整性校验
    # 参数合法性校验 huose_id是否存在
    # 参数完整, 并合法, 调用七牛上传图片的模块, 返回文件名, 将文件名等信息保存到数据库
    # 返回应答, 向用户返回图片路径, 也就是访问到七牛服务器保存图片的路径

    # 获取参数
    user_id = g.user_id
    image_file_obj = request.files.get("house_image")  # 返回的是一个文件对象
    house_id = request.form.get('houes_id')  # request.form 也支持多媒体表单的文本数据提取

    # 校验参数完整性
    if not all([image_file_obj, house_id]):
        return jsonify(errcode=RET.PARAMERR, errmsg='参数不完整')

    # 校验huose_id 是否存在于数据库中
    try:
        house = House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.NODATA, errmsg='房屋信息错误')

    # 如果通过了校验则上传图片
    image_data = image_file_obj.read()  # 读取出来的是二进制的对象
    # 调用七牛模块的方法, 上传图片到七牛服务器
    try:
        file_name = storage_image(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.THIRDERR, errmsg='保存图片失败')
    # 如果保存到第三方服务器成功就会返回文件名, 将文件名保存扫数据库中
    house_image = HouseImage(
        house_id=house_id,
        url = file_name
    )
    db.session.add(house_image)
    # 处理房屋的主要图片, 如果没有设置过就进行设置, 否则不设置
    if not house.index_image_url:
        house.index_image_url=file_name
        db.session.add(house)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errcode=RET.DBERR, errmsg='保存房屋图片失败')

    # 设置图片的完整访问路径, 返回给用户
    image_url = constant.QINIU_URL_DOMIAN + file_name
    return jsonify(errcode=RET.OK, errmsg='上传成功', data={'image_url':image_url})


# 用户请求自己发布的房源信息条目
@api.route('/user/houses', methods=['GET'])
@login_required
def get_user_houses():
    """用户获取自己发布的房源信息条目"""
    # 判断用户是否登录, 未登录直接终止请求, 装饰器实现
    user_id = g.user_id
    try:
        user = User.query.get(user_id)
        houses = user.houses
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='查询失败')

    # 将查询到的数据转换为字典放到列表中
    houses_list = []
    if houses:
        for house in houses:
            houses_list.append(house.to_base_dict())
    return jsonify(errcode=RET.OK, errmsg='ok', data={'houses':houses_list})


# 用户进行房屋的列表查询
@api.route('/houses', methods=['GET'])
def get__house_info():
    """用户根据需求查询房屋信息"""
    # 参数: 期望查询的起始事件sd, 结束时间ed, 城区aid, 排序方式sk,请求的分页页码数p
    start_date_str = request.args.get("sd")
    end_date_str = request.args.get("ed")
    area_id = request.args.get("aid")
    sort_key = request.args.get("sk", "new")
    page = request.args.get("p", "1")

    # 参数校验, 如果传递了参数就进行判断
    # 判断时间格式是否正确
    # datetime.strptime()  # 字符串 -> datetime 类型
    # datetime.strftime()  # datetime -> 字符串 类型
    # datetime.strptime(要转换的时间字符串, 格式说明)
    # datetime.strptime("2018-01-01 23:08:08", "%Y-%m-%d %H:%M:%S")
    start_date, end_date = None, None
    try:
        if start_date_str: # 如果传递这个参数
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")  # 如果转换失败抛出异常
        if end_date_str:
            end_date = datetime.strftime(end_date_str, "%Y-%m-%d")  # 如果转换失败抛出异常
        if start_date and end_date:
            # 使用断言, 当assert 后面的条件为真时, 程序正常执行, 当assert后面的条件为假时, 停止执行, 抛出异常
            assert start_date <= end_date
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.PARAMERR, errmsg='日期信息有误')

    # 如果传递了城区信息, 就对其进行判断
    if area_id:
        try:
            area = Area.query.get(area_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errcode=RET.DBERR, errmsg="数据库异常, 查询失败")
        if area is None:
            return jsonify(errcode=RET.NODATA, errmsg='城区信息有误')

    # 判断页数
    try:
        int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 先尝试从redis中获取缓存
    redis_key = "house_list_%s_%s_%s_%s" % (start_date_str, end_date_str, area_id, sort_key)
    try:
        resp_json_str = redis_store.hget(redis_key)
    except Exception as e:
        current_app.logger.error(e)
    else:
        if resp_json_str:
            return resp_json_str, 200 , {"Content-Type": "application/json"}

    # 如果从没有从redis中查询到数据, 则从数据库中查询
    # 如果数据都合法, 则进行数据查询
    filter_params = []

    # 如果传递了城区参数
    # 在python 中, 比较运算符实际是通过方法实现的, flask将 == 对应的方法进行重写
    # == __eq__  # e equal
    # > __gt__  # g  greater  t  than
    # < __lt__  # l  less   t than
    # >= __ge__
    # <= __le__
    if area_id:
        filter_params.append(House.area_id == area_id )

    # 如果传递了时间参数
    # 思路一  错误
    # 在订单表中查询
    # 与用户想要入住的时间  不冲突  的订单房屋都有哪些
    # bug: 会遗漏那些没有被下过订单的房屋

    # 思路二 正确
    # 在订单表中查询
    #    与用户想要入住的时间  冲突  的订单房屋有哪些，也就是不能预订的
    # conflict_house_obj_list = Order.query.filter(冲突的条件).all()

    # 冲突的条件， 比较是否有时间交集，如果有，表示冲突
    # Order.begin_date Order.end_date  start_date用户预期的起始时间 end_date用户预期的结束时间
    # Order.begin_date <= end_date and Order.end_date >= start_date

    # conflict_house_id_list = [house_obj.id for house_obj in conflict_house_obj_list]
    # 然后在房屋表中 查询排除冲突之后的剩下的房屋 （不会再遗漏那些没有被下过订单的房屋）
    # select * from ih_house_info where id not in (冲突的房屋id)

    conflict_house_obj_list = None

    try:
        # 当用户填写了开始日期和结束日期
        # 冲突的房屋订单
        if start_date and end_date:
            conflict_house_obj_list = Order.query.fileter(Order.begin_date <= end_date, Order.end_date >= start_date).all()
        # 当用户只填写了开始时间
        if  start_date:
            conflict_house_obj_list = Order.query.filter(Order.end_date >= start_date).all()
        # 当用户只填写了结束时间
        if end_date:
            conflict_house_obj_list = Order.query.filter(Order.begin_date <= end_date).all()

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='数据库异常, 暂时无法查询')

    # 如果conflict_house_obj_list 不为None, 则存在冲突订单, 在查询房屋时将其过滤掉
    if conflict_house_obj_list:
        # 冲突房屋的id
        conflict_house_id_list = [house_obj.house_id for house_obj in conflict_house_obj_list]
        # 向查询条件中添加过滤不冲突的房屋的条件
        filter_params.append(House.id.notin_(conflict_house_id_list))

    # House.query.filter(House.area_id == area_id, House.id.notin_(conflict_house_id_list))
    query = House.query.filter(*filter_params)

    # 补充排序条件
    if sort_key == "booking":
        query = query.order_by(House.order_count.desc())
    elif sort_key == "pri-inc":
        query = query.order_by(House.price)
    elif sort_key == "price-dec":
        query = query.order_by(House.price.desc())
    else:
        # 用户没有传递排序条件, 按房源时间新旧排序
        query = query.order_by(House.create_time.desc())

    # 处理分页
    # query.paginate(页数(页码数), per_page=每页容量, error_out=False 关闭自动错误输出)
    try:
        page_obj = query.paginate(page, per_page=constant.HOUSE_LIST_PER_PAGE_COUNT, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='数据库异常')

    # 获取页面数据
    house_obj_list = page_obj.items
    # 获取符合条件的总的页数
    total_pages = page_obj.pages
    # 当查询页数大于总页数时
    if page > total_pages:
        return jsonify(errcode=RET.PARAMERR, errmsg='参数错误')
    # 遍历结果转换为字典
    house_dict_list = []
    for house_obj in house_obj_list:
        house_dict_list.append(house_obj.to_base_dict())
    # 考虑将结果保存到redis中, 再次查找时直接到先到redis中进行查找, 使用哈希类型的数据进行保存, key 属性 值, 这里应该考虑到什么情况下数据库数据变化时,应该将redis中的缓存删除掉
    # 形成缓存数据
    resp = dict(errcode=RET.OK, errmsg='OK', data={"houses": house_dict_list, "pages": total_pages, "current_page": page})
    resp_json_str = json.dumps(resp)
    redis_key = "house_list_%s_%s_%s_%s" % (start_date_str, end_date_str, area_id, sort_key)
    # 将数据保存到redis中, 使用redis的管道工具, 一次性传递多个任务, 避免多次访问redis数据库
    try:
        # 创建redis管道工具对象
        pipe = redis_store.pipeline()
        # 开启管道让其接收多条命令
        pipe.multi()
        # 通过pipe管道添加要执行的命令
        pipe.hset(redis_key, page, resp_json_str)
        pipe.expire(redis_key, constant.HOUSE_LIST_REDIS_CACHE_EXPIRES)
        # 管道执行命令
        pipe.execute()
    except Exception as e:
        current_app.logger.error(e)
    # 返回应答
    return resp_json_str, 200, {'Content-Type':"application/json"}


# 用户进行房屋的详情查询
# get /houses/<int:house_id>
@api.route('/houses/<int:house_id>', methods=['GET'])
def get_house_detail(house_id):
    """获取房屋详情"""
    # 参数获取
    # 参数完整性校验
    # 参数合法性校验, 数据库是否存在该房屋
    # 房屋详情查询, 先向redis中查询
    # 如果redis中不存在该房屋的详情, 则向数据库中查询, 并将查询结果保存到redis中
    # 完整业务处理, 返回应答

    # 前端在房屋详情页面展示时，如果浏览页面的用户不是该房屋的房东，则展示预定按钮，否则不展示，
    # 所以需要后端返回登录用户的user_id
    # 尝试获取用户登录的信息，若登录，则返回给前端登录用户的user_id，否则返回user_id=-1
    user_id = session.get("user_id", "-1")
    # 获取参数, house_id 直接当做路径进行传递, 使用转换器, 进行获取
    if not house_id:
        return jsonify(errcode=RET.PARAMERR, errmsg='参数错误')
    # 先尝试从redis中获取信息 str key value  house_info_house_id  resp_json_str
    try:
        resp_json_str = redis_store.get('house_info_%s' % house_id)
    except Exception as e:
        current_app.logger.error(e)
    else:
        if resp_json_str:
            current_app.logger.info("hit house info redis")
            return resp_json_str, 200, {"Content-Type": "application/json"}
    # 如果从redis中没有取到数据, 则向数据库中获取
    try:
        house_obj = House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='数据库异常')
    if not house_obj:
        return jsonify(errcode=RET.NODATA, errmsg='房屋不存在, 请确认后重新查询')
    # 将数据装化为字典数据
    resp = house_obj.to_full_dict()
    resp_dict = dict(errcode=RET.OK, errmsg='查询成功', data={'user_id':user_id, 'house':resp})
    resp_json_str = json.dumps(resp_dict)
    # 将数据保存到redis中
    try:
        redis_store.setex("house_info_%s" % house_id, constant.HOUSE_DETAIL_REDIS_EXPIRE_SECOND, resp_json_str)
    except Exception as e:
        current_app.logger.error(e)
    # 返回应答
    return resp_json_str, 200, {"Content-Type": "application/json"}
