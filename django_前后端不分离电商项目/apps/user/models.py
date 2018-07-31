from django.db import models

# 导入django默认的认证系统包,使用认证系统自带的模型创建用户相关字段  如果在这里就是不使用django的认证系统,那视图内岂不是不能使用认证系统
# 判断用户是否登录? 自己怎么实现
from django.contrib.auth.models import AbstractUser   # 该包下有个模块的名字和这个很相似becareful
# 导入抽象模型基类
from db.base_model import BaseModel


# 使用django默认的认证系统的类去创建模型
class User(AbstractUser, BaseModel):
    """用户模型类"""
    # 指定数据表的名字，以及后台管理系统显示字段的名字
    class Meta:
        # 指定数据表的名字
        db_table = 'df_user'
        # 指定后台管理系统显示字段的名字
        verbose_name = '用户'
        # 让设置的后台管理系统的名字和设置的一致
        verbose_name_plural = verbose_name


# 地址模型管理器类
class AddressManager(models.Manager):
    # 1.改变原有查询的结果集
    # 2.添加额外的方法：操作self所在的模型类对应的数据表（增删改查)
    def get_default_address(self, user):
        try:
            address = Address.objects.get(user=user, is_default=True)
        except Address.DoesNotExist:
            address = None
        return address


# 创建地址模型类
class Address(BaseModel):
    user = models.ForeignKey('User', verbose_name='所属账户')
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr = models.CharField(max_length=256, verbose_name='收件地址')
    zip_code = models.CharField(max_length=7, null=True, verbose_name='邮政编码')
    phone = models.CharField(max_length=11, verbose_name='联系电话')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')

    # 自定义模型管理器类的对象
    objects = AddressManager()

    # 指定数据表的名字和后台管理系统显示的名字
    class Meta:
        db_table = 'df_address'
        # 指定后台管理系统显示字段的名字,verbose_name的变量名字是固定使用这个
        verbose_name = '地址'
        # 让后台管理系统显示的名字与设置的一致
        verbose_name_plural = verbose_name