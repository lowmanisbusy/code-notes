from django.db import models


# 创建所有的模型的基类
class BaseModel(models.Model):
    """抽象模型基类"""
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now_add=True, verbose_name='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='是否删除')

    # 不加这一句可能会出现很多错误,为什么
    class Meta:
        # 指定这个类是一个抽象模型类
        abstract = True