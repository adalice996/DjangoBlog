import logging

from django.contrib import admin
# Register your models here.
from django.urls import reverse
from django.utils.html import format_html

# 获取logger实例，用于记录日志
logger = logging.getLogger(__name__)


class OAuthUserAdmin(admin.ModelAdmin):
    """
    OAuth用户模型的Admin管理界面配置
    用于在Django Admin中管理第三方登录的用户信息
    """
    
    # 搜索字段配置
    search_fields = ('nickname', 'email')
    # 每页显示的记录数
    list_per_page = 20
    # 列表中显示的字段
    list_display = (
        'id',
        'nickname',
        'link_to_usermodel',  # 自定义字段：链接到用户模型
        'show_user_image',    # 自定义字段：显示用户头像
        'type',
        'email',
    )
    # 可点击进入编辑页面的字段
    list_display_links = ('id', 'nickname')
    # 右侧过滤器配置
    list_filter = ('author', 'type',)
    # 只读字段列表
    readonly_fields = []

    def get_readonly_fields(self, request, obj=None):
        """
        动态设置所有字段为只读，防止在admin中修改OAuth用户数据
        """
        return list(self.readonly_fields) + \
               [field.name for field in obj._meta.fields] + \
               [field.name for field in obj._meta.many_to_many]

    def has_add_permission(self, request):
        """
        禁用添加权限，OAuth用户只能通过第三方登录自动创建
        """
        return False

    def link_to_usermodel(self, obj):
        """
        自定义字段：显示链接到关联的本地用户模型
        """
        if obj.author:
            # 获取关联用户模型的app和model信息
            info = (obj.author._meta.app_label, obj.author._meta.model_name)
            # 生成用户编辑页面的URL
            link = reverse('admin:%s_%s_change' % info, args=(obj.author.id,))
            # 返回格式化的HTML链接
            return format_html(
                u'<a href=" ">%s</a >' %
                (link, obj.author.nickname if obj.author.nickname else obj.author.email))

    def show_user_image(self, obj):
        """
        自定义字段：显示用户头像
        """
        img = obj.picture
        # 返回格式化的图片HTML，设置固定尺寸
        return format_html(
            u'< img src="%s" style="width:50px;height:50px"></img>' %
            (img))

    # 设置自定义字段在admin中的显示名称
    link_to_usermodel.short_description = '用户'
    show_user_image.short_description = '用户头像'


class OAuthConfigAdmin(admin.ModelAdmin):
    """
    OAuth配置模型的Admin管理界面配置
    用于管理第三方登录的应用配置信息
    """
    
    # 列表中显示的字段
    list_display = ('type', 'appkey', 'appsecret', 'is_enable')
    # 右侧过滤器配置
    list_filter = ('type',)
