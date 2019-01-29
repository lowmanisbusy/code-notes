# coding:utf-8

# 图片验证码在redis中保存的有效期，单位：秒
IMAGE_CODE_REDIS_EXPIRES = 300

# 短信验证码的有效期，单位：秒
SMS_CODE_REDIS_EXPIRES = 300

# 验证码短信模板编号, 在云通讯平台中, 短信模板种类有多种
SMS_CODE_TEMPLATE = 1

# 两次发送短信验证码的时间间隔，单位：秒
SEND_SMS_CODE_INTERVAL = 60

# 错误登录的最大尝试次数
WRONG_LOGIN_MAX_TIMES = 5

# 登录错误封堵ip的时间，单位：秒
WRONG_LOGIN_FORBID_TIME = 5*60*60

# 设置存储在redis中的城区缓存信息的过期时间 单位:秒
AREA_INFO_REDIS_CACHE_EXPIRES = 7200

# 七牛云空间保存图片的公共域名路径
QINIU_URL_DOMIAN = ""

# 房屋详情页面数据Redis缓存时间，单位：秒
HOUSE_DETAIL_REDIS_EXPIRE_SECOND = 7200

# 房屋详情页展示的评论最大数
HOUSE_DETAIL_COMMENT_DISPLAY_COUNTS = 30

# 房屋列表页数据每页数量
HOUSE_LIST_PER_PAGE_COUNT = 2

# 房屋列表页面数据redis缓存时间，单位：秒
HOUSE_LIST_REDIS_CACHE_EXPIRES = 3600

