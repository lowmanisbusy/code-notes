# coding=utf-8
import re

from flask import current_app, request, jsonify, session, g

from . import api
from ihome import db, models
from ihome.utils.response_code import RET
from ihome import redis_store
# 导入这个方法可以对密码进行 sha256 + 盐值 的方式进行加密, 加密之后才保存在数据库
# 以防数据库被攻击后, 密码泄露
from werkzeug.security import generate_password_hash
from werkzeug import security  # 导入这个模块,将使用generate_password_hash()进行加密的密码和输入的密码进行对比, 判断是否相等
from sqlalchemy.exc import IntegrityError  # 对应到数据库中出现重复记录的错误异常
from ihome import constant
from ihome.utils.common_dicorator import login_required
from ihome.utils.qi_niu_storage import storage_image


# POST /user/register   参数以请求体json格式进行传递
@api.route('/user/register', methods=['POST'])
def register():
    """注册"""
    # 获取参数 手机号, 短信验证码, 密码, 确认 密码
    req_dict = request.get_json()  # 使用request对像的get_son()可以取得请求体中的json数据, 返回的是一个字典
    pho_num = req_dict.get('mobile')
    sms_code = req_dict.get('sms_code')
    password = req_dict.get('password')
    password_checked = req_dict.get('password_checked')
    # 校验参数完整性
    if not all([pho_num, sms_code, password, password_checked]):
        return jsonify(errcode=RET.PARAMERR, errmsg='数据不完整')

    # 校验参数合法性
    # 校验手机格式合法性
    result = re.match(r'1[3456789]\d{9}', pho_num)
    if not result:
        # 手机格式不合法
        return jsonify(errcode=RET.PARAMERR, errmsg='手机号码格式错误')
    # 判断两次填写的密码是否一致
    if password != password_checked:
        return jsonify(errcode=RET.PARAMERR, errmsg='两次输入的密码不一致')
    # 校验手机验证码是否正确
    # 从redis数据库取到验证码
    try:
        real_sms_code = redis_store.get('sms_code_%s' % pho_num)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='数据库异常')
    if real_sms_code is None:
        # 表示短信验证码已过期
        return jsonify(errcode=RET.NODATA, errmsg='验证码已失效')
    # 将数据库的验证码与用户发送过来的验证码进行校验
    if sms_code != real_sms_code:
        return jsonify(errcode=RET.DATAERR, errmsg='短信验证码不正确')

    # hashlib.sha256(password).hexdigest()
    #                  盐值salt
    # A "123456" +  "dhfwoiehf"      -> sha256 ->       dhfwoiehf|dhosidhosifhodisfosfdosgfosdgsofdhsoshof
    # B "123456" +  "dwoiefhow"      -> sha256 ->        hdoiwydowodfgwudfgiwgfidwudfgiwdufgwifgwiw
    #
    #
    # 登录  用户明文
    # "123456" +  "dhfwoiehf"  -> sha256 ->  dhosidhosifhodisfosfdosgfosdgsofdhsoshof

    # 如果短信验证码正确, 就对用户的密码进行加密, 使用werkzeug提供的密码加密方法
    # 这个方法使用sha256 + 盐值 的方式进行加密
    password_hash = generate_password_hash(password)
    # # 将用户数据保存mysql数据中
    user = models.User(
        name=pho_num,
        password_hash = password_hash,
        mobile = pho_num
    )

    # 在模型类如果使用@property定义了获取密码和设置密码的函数, 可以使用类似设置属性的方法进行密码的设置
    # user = models.User(
    #     name=pho_num,
    #     password_hash='',  # 因为在模型类中定义了给密码属性赋值的函数, 所以这里给一个空白值
    #     mobile=pho_num
    # )
    # # 以给对象属性赋值的方式设置密码, 详细看模型类User中使用了装饰器property装饰的password的函数, 这里其实相当于传参
    # user.password = password

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError as e:
        # 数据库有存在相同的记录
        return jsonify(errcode=RET.DATAEXIST, errmsg='手机号已经被注册')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='数据库出现异常')
    # 使用session, 实现登录状态保持功能
    session['user_id'] = user.id
    session['name'] = pho_num
    session['pho_num'] = pho_num

    # 返回注册成功的消息
    # '{"errcode":"0", "errmsg": "注册成功", "data":{"user_id": xxxx}}'
    return jsonify(errcode=RET.OK, errmsg='注册成功', data={'user_id':user.id})


# 用户登录
# POST /user/login json格式传递数据
@api.route("/user/login", methods=['POST'])
def login():
    """用户登录, 为了防止恶意攻击者频繁使用登录操作访问网站, 当一个账号访问密码错误5c
    次, 设置一段时间内拒绝这个域名再次访问"""
    # 获取参数 手机号码, 密码
    # 检验参数完整性
    # 获取ip该用户的ip地址, 确认该用户已经输入密码或账号错误了几次
    # 判断使用户是否存在
    # 判断密码是否正确 password_hash = generate_password_hash(password)
    # 如若登录成功, 保持登录状态

    # 获取参数 手机号码
    req_dict = request.get_json()
    mobile = req_dict.get('mobile')
    password = req_dict.get('password')
    # 校验参数完整性
    if not all([mobile, password]):
        return jsonify(errcode=RET.PARAMERR, errmsg='参数不完整')

    # 校验手机号码是否合法
    if not re.match(r'1[3456789]\d{9}', mobile):
        return jsonify(errcode=RET.PARAMERR, errmsg='手机号码格式错误')
    # 根据用户的ip, 从redis中获取用户已经输错登录信息的次数
    user_ip = request.remote_addr  # 用户的ip地址
    try:
        wrong_login = redis_store.get('login_num_%s' % user_ip)
    except Exception as e:
        current_app.logger.error(e)
    else:
        # 判断这个ip地址的错误尝试次数, 这里是否应该直接限制掉ip和账号, 而不单单是账号
        if wrong_login is not None and int(wrong_login) >= (constant.WRONG_LOGIN_MAX_TIMES):
            # 如果错误次数超过限制, 验证访问
            return jsonify(errcode=RET.REQERR, errmsg='输入账号信息错误次数已达上限,暂时无法登录!!!')
    # 如果用户登录错误次数为超过次数, 则判断用户是否存在
    # 根据手机号从数据库中取出用户的真实加密密码，对用户的登录输入密码进行加密计算，比较两个值，
    try:
        user = models.User.query.filter_by(mobile=mobile).first()  # 这里加个first()方法就不用使用下标取出对象了
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode= RET.DBERR, errmsg='数据库异常')

    if user is None :
        # 表示用户的手机号错误   密码错误
        # 否则登录失败， 保存记录错误次数  "login_num_ip地址": "错误次数" 字符串类型
        # 如果用户是第一次错误尝试，redis中保存数据1
        # 如果不是第一次错误，redis中的数据需要累加1
        # 使用redis 的  incr 方法, 当这个键不存在时直接赋值为1, 存在就+1
        try:
            redis_store.incr('login_num_%s' % user_ip)
            # 设置限制的有限时间,这样设置主要是为了当错误次数达到上限时,限制这段时间内再次进行登录操作
            redis_store.expire('login_num_%s' % user_ip, constant.WRONG_LOGIN_FORBID_TIME)
        except Exception as e:
            current_app.logger.error(e)
        return jsonify(errcode=RET.DATAERR, errmsg='用户名错误, 请确认后重新输入')

    # 如果用户存在就判断密码是否正确
    # 使用security.check_password_hash()判断密码和加密后的密码是否是同一个密码
    result = security.check_password_hash(user.password_hash, password)  # 当密码一致是 返回true, 不一致false
    print(result)
    if not result:
        return jsonify(errcode=RET.PWDERR, errmsg='密码错误')

    # 如果用户名存在, 密码也正确那么同意用户登录请求
    # 使用session保存用户的登录的状态, 当向用户返回应答时, 会自动向用户返回带有session_id的cookie,session值不保存在客户端中,而是保存在redis中
    # 当前端发送请求时, 如果向前端发送了session 可以通过 session.get()取出数据, 需要从flask先导入session
    session['user_id'] = user.id
    session['user_name'] = user.name
    session['mobile'] = user.mobile
    # 返回应答
    return jsonify(errcode=RET.OK, errmsg='登录成功')


@api.route('/session', methods=['GET'])
def check_login():
    """确认登录状态"""
    # 尝试在用户的请求的信息中获取session, 其实就是从其中获取session_id, session是存储在redis里, 这些都是flask进行处理的
    name = session.get('user_name')
    # 如果在请求信息获取到了一同发送过来的session, 那么说明用户已经登录, 否则未登录
    if name is not None:
        return jsonify(errcode=RET.OK, errmsg="true", data={"name": name})
    else:
        return jsonify(errcode=RET.SESSIONERR, errmsg="false")


@api.route('/session', methods=['DELETE'])
def login_out():
    """登出操作"""
    # 直接删除session即可
    session.clear()
    return jsonify(errcode=RET.OK, errmsg='OK')


# 用户进行上传头像图片的操作, 使用自定义的装饰器验证用户是否登录
@api.route('/user/avatars', methods=['POST'])
@login_required
def upload_avatar():
    """保存用户的头像
        参数： 头像图片(多媒体表单）   user_id (通过g对象获取）
        """
    # 获取头像数据, 通过files 可以获取上床文件的所有的对象 在使用get 获取具体对象
    image_file_obj = request.files.get('avatar')
    # 在装饰器中通过g 保存了user_id , 这里再通过g 取回, 单个g对象只在当前轮请求有效
    user_id = g.user_id

    # 校验数据
    if image_file_obj is None:
        return jsonify(errcode=RET.PARAMERR, errmsg='文件异常')

    # 调用自定义的方法, 将图片上传到七牛服务器
    # 先读取图片对象的内容, 读取到的是二进制数据
    file_data = image_file_obj.read()
    # 上传图片, 返回文件名
    try:
        file_name = storage_image(file_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.THIRDERR, errmsg='上传图片失败')

    # 将文件的信息保存到数据库中
    # user = User.query.get(user_id)
    # user.avatar_url = file_name
    # db.session.add(user)
    # db.commit()

    try:
        # 使用update 在查询的同时,更新数据, 保存的是图片路径(七牛服务器+文件名
        user = models.User.query.filter_by(id=user_id).update({'avatar_url':file_name})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='保存图片失败')
    # 编辑图片完整路径, 先在七牛服务器获取地址
    avatar_url = constant.QINIU_URL_DOMIAN + file_name
    # 返回应答
    return jsonify(errcode=RET.OK, errmsg='保存成功', data={'avatar_url': avatar_url})


@api.route("/user/name", methods=["PUT"])
@login_required
def change_name():
    """修改用户名"""
    # 装饰器判断用户是否登录
    # 获取用户的user_id, 使用g对象
    user_id = g.user_id

    # 获取修改后的用户名, 因为是传输的是json格式的数据, 返回字典
    data = request.get_json()
    # 校验参数完整性
    if not data:
        return jsonify(errcode=RET.PARAMERR, errmsg="参数不完整")
    name = data.get('name')
    # 校验用户名是否为空
    if not name:
        return jsonify(errcode=RET.PARAMERR, errmsg="用户名不能为空")

    # 校验用户名是否已经存在, 如果不存在则直接更新, name字段是唯一值
    try:
        models.User.query.filter_by(id=user_id).update({"name": name})
        db.session.commit()
    except IntegrityError as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errcode=RET.DATAEXIST, errmsg='用户名已存在')
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errcode=RET.DBERR, errmsg="设置失败, 请稍后再试")
    # 修改session中的name字段
    session['name'] = name
    # 修改成功返回应答, session
    return jsonify(errcode=RET.OK, errmsg="OK", data={"name":name})


@api.route('/user', methods=['GET'])
@login_required
def get_user_profile():
    """获取用户个人信息"""
    user_id = g.user_id
    # 查询数据库,获取个人信息
    try:
        user = models.User.query.get(user_id)  # 使用get()过滤器就可以直接获取传递id值的对象
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='获取失败')
    if user is None:
        return jsonify(errcode=RET.NODATA, errmsg='用户不存在')
    return jsonify(errcode=RET.OK, errmsg='OK', data=user.to_dict())


@api.route('/user/auth', methods=['GET'])
@login_required
def get_user_auth():
    """获取用户的实名认证信息"""
    user_id = g.user_id
    try:
        user = models.User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='查询失败')
    if user is None:
        return jsonify(errcode=RET.NODATA, errmsg='无效操作')
    return jsonify(errcode=RET.OK, errmsg='OK', data=user.auth_to_dict())


@api.route('/user/auth', methods=['POST'])
@login_required
def set_user_auth():
    """保存用户的实名认证信息"""
    user_id = g.user_id
    req_data = request.get_json() # 返回的是字典
    if not req_data:
        return jsonify(errcode=RET.PARAMERR, errmsg='参数错误')
    real_name = req_data.get('real_name')
    id_card = req_data.get('id_card')

    # 参数校验
    if not all([real_name, id_card]):
        return jsonify(errcode=RET.PARAMERR, errmsg='数据不完整')

    # 保存用户的实名认证信息
    try:
        models.User.query.filter_by(id=user_id, real_name=None, id_card=None)\
            .update({'real_name':real_name, 'id_card':id_card})
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errcode=RET.DBERR, errmsg='保存实名信息失败')
    return jsonify(errcode=RET.OK, errmsg='保存成功')
