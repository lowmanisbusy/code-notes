# -*- coding:utf-8 -*-


from datetime import datetime
from . import db
from werkzeug import security
from ihome import constant


class BaseModel(object):
    """模型基类，为每个模型补充创建时间与更新时间"""
    # 为所有的数据表增加两个字段, 分别是创建时间, 和更新的时间, 便于提取数据行的信息
    create_time = db.Column(db.DateTime, default=datetime.now)  # 记录的创建时间
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)  # 记录的更新时间


class User(BaseModel, db.Model):
    """用户"""
    # 定义数据库中表的名字
    __tablename__ = "ih_user_profile"

    id = db.Column(db.Integer, primary_key=True)  # 用户编号
    name = db.Column(db.String(32), unique=True, nullable=False)  # 用户暱称
    password_hash = db.Column(db.String(128), nullable=False)  # 加密的密码
    mobile = db.Column(db.String(11), unique=True, nullable=False)  # 手机号
    real_name = db.Column(db.String(32))  # 真实姓名
    id_card = db.Column(db.String(20))  # 身份证号
    avatar_url = db.Column(db.String(128))  # 用户头像路径
    houses = db.relationship("House", backref="user")  # 用户发布的房屋
    orders = db.relationship("Order", backref="user")  # 用户下的订单

    # property装饰器将方法变成属性password
    # 当使用@property装饰了一个函数时,就可以使用获取属性值的一样的方式调用函数
    # 调用时属性名就是函数名 不用加括号
    # password = user.password 然后在password函数内 内实现业务处理
    @property
    def password(self):
        """
        对应额外添加的属性password的读取行为
        """
        # 在我们这个应用场景中，读取密码没有实际意义
        # 所以对于password属性的读取行为的函数不再实现
        # 通常以抛出AttributeError的方式来作为函数代码
        raise AttributeError("不支持读取操作")

    # 如果一个方法使用了装饰器@password.setter  这里的password 就是上边实现了读取行为的函数名
    # 也是实现本函数名子, (名字必须一致),这时就可以直接使用 对象名.函数名=参数 给这个函数进行传参,这时就像给这个对象的属性赋值
    @password.setter
    def password(self, password):
        """
        对应额外添加的属性password的设置行为
        : params origin_p# 如果传递了时间参数
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
    assword: 在进行属性设置的时候，要设置的值  # user.password = origin_password
        :return:
        """
        self.password_hash = security.generate_password_hash(password)

    def check_password(self, origin_password):
        """检验用户的密码是否正确
        : param origin_password:  用户登录时输入的原始密码
        """
        return security.check_password_hash(self.password_hash, origin_password)

    def to_dict(self):
        """将对象的属性装换为字典数据"""
        user_dict = {
            "user_id": self.id,
            "name": self.name,
            "mobile": self.mobile,
            "avatar": constant.QINIU_URL_DOMIAN + self.avatar_url if self.avatar_url else "",  # 后面的写法是python的三目写法
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S")  # 将时间字符串化(括号内为时间的显示格式)
        }
        return user_dict

    def auth_to_dict(self):
        """将实名信息转化为字典数据"""
        auth_dict = {
            'user_id': self.id,
            'real_name': self.real_name,
            'id_card': self.id_card
        }
        return auth_dict


class Area(BaseModel, db.Model):
    """城区"""

    __tablename__ = "ih_area_info"

    id = db.Column(db.Integer, primary_key=True)  # 区域编号
    name = db.Column(db.String(32), nullable=False)  # 区域名字
    houses = db.relationship("House", backref="area")  # 区域的房屋

    # 在模型里定义一个方法, 将具体的area对象里的信息保存到字典里
    def to_dict(self):
        """将对象转换为对象"""
        d = {
            'aid': self.id,
            'aname': self.name
        }
        return d

# 房屋设施表，建立房屋与设施的多对多关系
house_facility = db.Table(
    "ih_house_facility",
    # 设置两个都是主键, 就是联合主键, 组合起来的情况是唯一的
    db.Column("house_id", db.Integer, db.ForeignKey("ih_house_info.id"), primary_key=True),  # 房屋编号
    db.Column("facility_id", db.Integer, db.ForeignKey("ih_facility_info.id"), primary_key=True)  # 设施编号
)


class House(BaseModel, db.Model):
    """房屋信息"""

    __tablename__ = "ih_house_info"

    id = db.Column(db.Integer, primary_key=True)  # 房屋编号
    user_id = db.Column(db.Integer, db.ForeignKey("ih_user_profile.id"), nullable=False)  # 房屋主人的用户编号
    area_id = db.Column(db.Integer, db.ForeignKey("ih_area_info.id"), nullable=False)  # 归属地的区域编号
    title = db.Column(db.String(64), nullable=False)  # 标题
    price = db.Column(db.Integer, default=0)  # 单价，单位：分
    address = db.Column(db.String(512), default="")  # 地址
    room_count = db.Column(db.Integer, default=1)  # 房间数目
    acreage = db.Column(db.Integer, default=0)  # 房屋面积
    unit = db.Column(db.String(32), default="")  # 房屋单元， 如几室几厅
    capacity = db.Column(db.Integer, default=1)  # 房屋容纳的人数
    beds = db.Column(db.String(64), default="")  # 房屋床铺的配置
    deposit = db.Column(db.Integer, default=0)  # 房屋押金
    min_days = db.Column(db.Integer, default=1)  # 最少入住天数
    max_days = db.Column(db.Integer, default=0)  # 最多入住天数，0表示不限制
    order_count = db.Column(db.Integer, default=0)  # 预订完成的该房屋的订单数
    index_image_url = db.Column(db.String(256), default="")  # 房屋主图片的路径
    # 只能一个这样的字段, 可以通过这个属性, 找到这个房子所有的设施 第一个参数是关联的表, 第二个参数是第二关联表
    # 通过这个属性, 返回的是一个个设施的对象
    facilities = db.relationship("Facility", secondary=house_facility)
    images = db.relationship("HouseImage")  # 房屋的图片
    orders = db.relationship("Order", backref="house")  # 房屋的订单

    def to_base_dict(self):
        """将房屋的基本信息转化为字典数据"""
        house_dict = {
            "house_id": self.id,
            "title": self.title,
            "price": self.price,
            "area_name": self.area.name,
            "img_url": constant.QINIU_URL_DOMIAN + self.index_image_url if self.index_image_url else "",
            "room_count": self.room_count,
            "order_count": self.order_count,
            "address": self.address,
            "user_avatar": constant.QINIU_URL_DOMIAN + self.user.avatar_url if self.user.avatar_url else "",
            "ctime": self.create_time.strftime("%Y-%m-%d")
        }
        return house_dict

    def to_full_dict(self):
        """将详细信息转换为字典数据"""
        house_dict = {
            "hid": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name,
            "user_avatar": constant.QINIU_URL_DOMIAN + self.user.avatar_url if self.user.avatar_url else "",
            "title": self.title,
            "price": self.price,
            "address": self.address,
            "room_count": self.room_count,
            "acreage": self.acreage,
            "unit": self.unit,
            "capacity": self.capacity,
            "beds": self.beds,
            "deposit": self.deposit,
            "min_days": self.min_days,
            "max_days": self.max_days,
        }

        # 房屋图片
        img_urls = []
        for image in self.images:
            img_urls.append(constant.QINIU_URL_DOMIAN + image.url)
        house_dict['img_urls'] = img_urls

        # 房屋设施
        facilities= []
        for facility in self.facilities:
            facilities.append(facility.id)
        house_dict['facilities'] =  facilities

        # 评论信息
        comments = []
        orders = Order.query.filter(Order.house_id == self.id, Order.status == "COMPLETE", Order.comment != None)\
            .order_by(Order.update_time.desc()).limit(constant.HOUSE_DETAIL_COMMENT_DISPLAY_COUNTS)
        for order in orders:
            comment = {
                "comment": order.comment,  # 评论的内容
                "user_name": order.user.name if order.user.name != order.user.mobile else "匿名用户",  # 发表评论的用户
                "ctime": order.update_time.strftime("%Y-%m-%d %H:%M:%S")  # 评价的时间
            }
            comments.append(comment)
        house_dict["comments"] = comments
        return house_dict


class Facility(BaseModel, db.Model):
    """设施信息"""

    __tablename__ = "ih_facility_info"

    id = db.Column(db.Integer, primary_key=True)  # 设施编号
    name = db.Column(db.String(32), nullable=False)  # 设施名字


class HouseImage(BaseModel, db.Model):
    """房屋图片"""

    __tablename__ = "ih_house_image"

    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey("ih_house_info.id"), nullable=False)  # 房屋编号
    url = db.Column(db.String(256), nullable=False)  # 图片的路径


class Order(BaseModel, db.Model):
    """订单"""

    __tablename__ = "ih_order_info"

    id = db.Column(db.Integer, primary_key=True)  # 订单编号
    user_id = db.Column(db.Integer, db.ForeignKey("ih_user_profile.id"), nullable=False)  # 下订单的用户编号
    house_id = db.Column(db.Integer, db.ForeignKey("ih_house_info.id"), nullable=False)  # 预订的房间编号
    begin_date = db.Column(db.DateTime, nullable=False)  # 预订的起始时间
    end_date = db.Column(db.DateTime, nullable=False)  # 预订的结束时间
    days = db.Column(db.Integer, nullable=False)  # 预订的总天数
    house_price = db.Column(db.Integer, nullable=False)  # 房屋的单价
    amount = db.Column(db.Integer, nullable=False)  # 订单的总金额
    status = db.Column(  # 订单的状态
        db.Enum(
            "WAIT_ACCEPT",  # 待接单,
            "WAIT_PAYMENT",  # 待支付
            "PAID",  # 已支付
            "WAIT_COMMENT",  # 待评价
            "COMPLETE",  # 已完成
            "CANCELED",  # 已取消
            "REJECTED"  # 已拒单
        ),
        default="WAIT_ACCEPT", index=True)
    comment = db.Column(db.Text)  # 订单的评论信息或者拒单原因

    def to_dict(self):
        """将订单信息转换为字典数据"""
        order_dict = {
            "order_id": self.id,
            "title": self.house.title,
            "img_url": constant.QINIU_URL_DOMIAN + self.house.index_image_url if self.house.index_image_url else "",
            "start_date": self.begin_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "ctime": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "days": self.days,
            "amount": self.amount,
            "status": self.status,
            "comment": self.comment if self.comment else ""
        }
        return order_dict
