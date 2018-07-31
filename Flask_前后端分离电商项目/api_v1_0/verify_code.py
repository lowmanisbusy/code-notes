# coding=utf8

import random

# 导入jsonify包, 当前的项目核心应用app
from flask import jsonify, current_app, request

# 导入应用视图蓝图
from . import api
# 导入生成验证码图片的工具包
from ihome.utils.captcha.captcha import captcha
# 导入连接redis数据库的连接实例
from ihome import redis_store, constant
# 导入视图业务处理结果的状态码(这些都是已经和前端协议好的处理结果状态码)
from ihome.utils.response_code import RET
# 导入发送验证短讯的工具包
from ihome.libs.yuntongxun.send_sms import CCP
# 导入模型类, 使用其对象
from ihome.models import User
# 从绝对路径导入使用了celery装饰的发送短信的方法
from ihome.celery_task.send_sms.tasks import send_sms


# GET /image_codes/图片验证码编号
@api.route('/image_codes/<image_code_id>')
def get_image_code(image_code_id):
    """提供图片验证码"""
    # 生成验证码图片
    # 使用redis str格式保存验证码内容信息 image_code_id编号(从前端生成地球上都只有唯一一个的编号)  验证码内容信息
    name, text, image_data = captcha.generate_captcha()  # 第一个是验证码图片名字 第二参数是真实验证码  第三个是验证码的背景图片

    # 保存验证码的真实值和这个验证码的编号, redis中, 有效期
    # redis数据类型: 字符串、列表、hash、set...
    # key:val
    # "image_code_编号1": "真实值",
    # "image_code_编号2": "真实值",
    # "image_code_编号3": "真实值",

    # redis_store.set(key, val)
    # redis_store.set("image_code_%s" % image_code_id, text)
    # redis_store.expire("image_code_%s"

    # redis 数据库连接实例有可能存在异常, 需要使用捕捉进行处理
    # setex()方法可以往redis写入数据时,加上有效时间
    try:
        redis_store.setex('image_code_%s' % image_code_id, constant.IMAGE_CODE_REDIS_EXPIRES, text)
        print(redis_store)
    except Exception as e:
        current_app.logger.error(e)  # 将错误写入日志
        return jsonify(errcode=RET.DBERR, errmsg='数据库异常')

    # 返回验证码图片
    # 直接在html页面中使用js不断动态生成验证码编号, 然后编辑请求路径, 将请求路径添加到相应的img src = '' 中,浏览器就会向后端发送请求
    return image_data, 200, {'Content-Type': 'image/jpg'}


# 发送短信验证码
# GET /sms_codes/手机号?image_code_id=xxx&image_code_text=xxx
@api.route('/sms_codes/<re(r"1[3456789]\d{9}"):pho_num>')
def send_sms_code(pho_num):
    """发送短信验证码"""
    # 提取参数
    image_code_id = request.args.get('image_code_id')
    image_code_text = request.args.get('image_code_text')
    # 校验参数完整性
    if not all([image_code_id, image_code_text]):
        return jsonify(errcode=RET.PARAMERR, errmsg='参数不完整')

    # 校验参数是否合法
    # 验证验证码是否正确, 从redis 取出真实值, 和客户端发送过来的值进行对比
    # 当和数据库进行连接查询操作时, 应该进行错误捕捉
    try:
        real_image_code_text = redis_store.get('image_code_%s' % image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errcode=RET.DBERR, errmsg='数据库异常')

    # 删除验证码图片, 一个验证码图片只能进行一次输入,
    try:
        redis_store.delete('image_code_%s' % image_code_id)
    except Exception as e:
        current_app.logger.error(e)

    # 判断验证码是否过期
    if real_image_code_text is None:
        return jsonify(errcode=RET.NODATA, errmsg='验证码已过期')

    # 将用户发送过来的验证码和从数据库取出的验证码图片进行校验
    if image_code_text.lower() != real_image_code_text.lower():
        # 用户填写的验证码错误
        return jsonify(errcode=RET.DATAERR, errmsg='验证码不正明确')

    # 业务逻辑处理, 如果图片验证码验证通过, 则进行短信业务处理
    # 判断手机号是否被注册过
    try:
        user = User.query.filter_by(mobile=pho_num).first()
    except Exception as e:
        current_app.logger.error(e)
    else:
        if user is not None:
            # 表示手机号被注册过
            return jsonify(errcode=RET.DATAEXIST, errmsg='该手机号已经被注册')

    # 手机号没有被注册
    # 判断是否在60秒内发送过短信, 是就终止请求
    try:
        flag = redis_store.get('send_sms_code_flag_%s' % pho_num)
    except Exception as e:
        current_app.logger.error(e)
    else:
        if flag is not None:
            # 表示60s内有发送过数据
            return jsonify(errcode=RET.REQERR, errmsg='短信发送过于频繁')

    # 用户没有在60s内重复发送短信
    # 生成短信验证码, %06d表示格式化显示，至少6位数字，不足6位前面补0
    sms_code = '%06d' % random.randint(100000, 999999)


    # # 连接第三方平台, 发送短信验证码
    # try:
    #     ccp = CCP()
    #     # 第一个参数是手机号码, 第二个是列表[要发送的消息, 消息的有效时间], 第三个是使用的短信模板编号
    #     result = ccp.send_template_sms(pho_num, [sms_code, str(constant.SMS_CODE_REDIS_EXPIRES // 60)],
    #                                    constant.SMS_CODE_TEMPLATE)
    # except Exception as e:
    #     current_app.logger.error(e)
    #     return jsonify(errcode=RET.THIRDERR, errmsg='短信发送异常')


    # 使用celery装饰发送短信的任务, 返回的是发布任务的任务对象
    #     # 第一个参数是手机号码, 第二个是列表[要发送的消息, 消息的有效时间], 第三个是使用的短信模板编号
    task_obj = send_sms.delay(pho_num, [sms_code, str(constant.SMS_CODE_REDIS_EXPIRES // 60)],
                                       constant.SMS_CODE_TEMPLATE)
    # 可以通过任务对象的get方法获取异步任务的结果, 默认是阻塞的
    result = task_obj.get()
    # 如果发送成功, 就保存短信验证码到redis数据, 返回应答
    if result == 0:
        try:
            redis_store.setex('sms_code_%s' % pho_num, constant.SMS_CODE_REDIS_EXPIRES, sms_code)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errcode=RET.DBERR, errmsg='保存短信验证码异常')
        # 保存短信发送的记录到redis 中, 可以用这个数据判断用户是否在60s内发送过短信
        try:
            redis_store.setex('send_sms_code_flag_%s' % pho_num, constant.SEND_SMS_CODE_INTERVAL, 1)
        except Exception as e:
            current_app.logger.error(e)
        return jsonify(errcode=RET.OK, errmsg='发送短信成功')
    else:
        return jsonify(errcode=RET.THIRDERR, errmsg='短信发送失败')
