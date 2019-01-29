# coding=utf8

from qiniu import Auth, put_file, put_data

# 需要填写你的 Access Key 和 Secret Key
access_key = ''  # 在七牛注册后获取值
secret_key = ''


def storage_image(file_data):  # 这个参数在视图中当用户上传图片时,读取到图片数据, 然后传参
    """将用户上传的图片上传到第三方云空间, 七牛服务器
    :param file_data:  要上传的文件的二进制数据
    :return: 正常:返回七牛保存的文件名
    """

    # 构建鉴权对象, 就是为了在七牛服务器上认证连接者的身份
    q = Auth(access_key, secret_key)

    # 要上传到七牛上的空间名称  # 开发者需要在七牛上先创建一个空间名称
    bucket_name = 'ihome'

    # 上传到七牛后保存的文件名, 我们不指定名字，由七牛决定文件名
    key = None

    # 生成上传的Token, 可以指定过期时间, 第一个参数名空间名称, 第二个是自己定义的文件名, 第三个是过期时间
    token = q.upload_token(bucket_name, key, 3600)

    # 上传文件的数据, 返回的ret里有上传文件后生成的文件名, info可以取出本次上传结果的信息
    ret, info = put_data(token, key, file_data)

    # 判断是否上传成功
    if info.status_code == 200:
        # 表示上传成功
        # 获取七牛保存的文件名
        file_name = ret.get('key')
        return file_name
    else:
        # 上传失败
        # return None
        raise Exception('上传图片失败')

if __name__ == '__main__':
    with open("./1.png", "rb") as f:
        file_data = f.read()
        file_name = storage_image(file_data)
        print(file_name)
