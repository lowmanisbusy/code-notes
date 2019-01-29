from django.core.files.storage import Storage # 引入django自带文件存储服务器类
from fdfs_client.client import Fdfs_client # 引入fdfs客户端模块
from django.conf import settings
import os

# 保存文件的时候，django系统会调用Storage类中save方法，save方法内部会调用文件存储类中的_save方法
# _save方法的返回值，会保存在表的image字段中
# 在调用save方法之前，django系统会先调用exists方法，判断文件的系统是否存在
# 因为在settings中指定了系统文件的存储类,所以当在后台管理页面中上传文件时会自动调用这里的方法


# 自定义文件存储类
class FDFSStorage(Storage):
    """fastdfs系统文件存储类"""
    # 后面两个参数必须传入,但是已经在settings中进行了设置,所以这里设置默认值为None
    def __init__(self, client_conf=None, nginx_url=None):
        """初始化"""
        # 如果没有指定,则使用自己在settings中设置的值,以此进行重置
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf
        if nginx_url is None:
            nginx_url = settings.FDFS_NGINX_URL
        self.nginx_url = nginx_url

    # 打开文件时使用, 必须有这个方法
    def _open(self, name, mode='rb'):
        pass

    # 保存文件时使用
    def _save(self, name, content):
        """保存文件时使用"""
        # name: 上传文件的名称
        # content: 包含上传文件内容的File对象

        # 创建client对象
        client = Fdfs_client(self.client_conf)
        content = content.read()

        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id, # 返回的文件的ID
        #     'Status': 'Upload successed.', # 上传是否成功
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # }

        # 把文件上传到fastdfs系统中,返回一个对象 包含本次上传相关的信息的对象
        res = client.upload_appender_by_buffer(content)
        # 判断上传文件是否成功
        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到fdfs系统失败')
        # 获取文件的ID
        file_id = res.get('Remote file_id')

        # 返回文件的ID
        return file_id

    def exists(self, name):
        """判断文件是否存在, 不存在返回假,已存在会返回True,因为fdfs中会为每个文件重新赋予一个id名称, 所以不用担心文件名重复, """
        return False

    def url(self, name):
        """返回一个可访问到文件的url路径"""
        # name: 文件id
        return self.nginx_url+name
