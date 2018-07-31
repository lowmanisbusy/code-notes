# coding=utf-8

from CCPRestSDK import REST

# 主帐号
accountSid= '8aaf070860e4d30b0160e9b963cb02ad'

# 主帐号Token
accountToken= '0aacb9e69717407693ed0c45f0e631d1'

# 应用Id
appId='8aaf070860e4d30b0160e9b9642002b3'

# 请求地址，格式如下，不需要写http://
serverIP='app.cloopen.com'

# 请求端口
serverPort='8883'

# REST版本号
softVersion='2013-12-26'


# 发送模板短信
# @param to 手机号码
# @param datas 内容数据 格式为数组 例如：{'12','34'}，如不需替换请填 ''
# @param $tempId 模板Id
class CCP(object):
    """自行封装的发送短信的工具类
        使用单例模式实现, 意图是让云通讯的工具REST对象的构建只被执行一次
        使得云通讯的初始化设置只被执行一次, 减少耗时
    """
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(CCP, cls).__new__(cls)
            # 初始化REST SDK
            cls.__instance.rest = REST(serverIP, serverPort, softVersion)
            cls.__instance.rest.setAccount(accountSid, accountToken)
            cls.__instance.rest.setAppId(appId)
        return cls.__instance

    def send_template_sms(self, to, datas, tempId):
        result = self.rest.sendTemplateSMS(to, datas, tempId)
        # 取得返回的状态码
        status_code = result.get('statusCode')
        if status_code == '000000':
            # 表示短信发送成功
            return 0
        else:
            # 表示短信发送失败
            return -1

if __name__ == '__main__':
    ccp = CCP()
    ccp.send_template_sms('15347405654', [1234, 5], 1)
