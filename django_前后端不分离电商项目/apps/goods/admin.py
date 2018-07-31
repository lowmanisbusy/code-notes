from django.contrib import admin
# 导入缓存模块, 当某个模型下的数据被修改时, 清楚掉之前设置的缓存
from django.core.cache import cache
# 导入模型, 进行注册
from goods.models import GoodsType, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner


# 基类
class BaseAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        """新增或者更新数据时被调用"""
        # 调用父类方法, 完成新增或者更新操作(非删除的更新)
        super(BaseAdmin, self).save_model(request, obj, form, change)

        # 导入 celery任务,当存在更新时, 就向celery worker发送任务, 更新首页内容,放在外面为何导不进 ?????为什么
        from celery_tasks.tasks import generate_static_index_html

        # 附加操作
        generate_static_index_html.delay()
        # 附加操作, 清除现有首页缓存(因为首页数据已更新原有缓存已无用
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        """删除数据时被调用"""
        # 调用父类的方法，完成删除的操作
        super(BaseAdmin, self).delete_model(request, obj)

        # 导入 celery任务,当存在更新时, 就向celery worker发送任务, 更新首页内容,放在外面为何导不进 ?????为什么
        from celery_tasks.tasks import generate_static_index_html

        # 附加操作
        generate_static_index_html.delay()
        # 附加操作: 清除首页数据
        cache.delete('index_page_data')


class GoodsTypeAdmin(BaseAdmin):
    pass


class IndexGoodsBannerAdmin(BaseAdmin):
    pass


class IndexTypeGoodsBannerAdmin(BaseAdmin):
    pass


class IndexPromotionBannerAdmin(BaseAdmin):
    pass


# 注册模型, 当启动后后台管理页面后, 因为继承了父类的方法,有修改操作, 这里的方法就会被执行
admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
