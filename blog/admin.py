from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

# 注册模型到Django管理后台
from .models import Article, Category, Tag, Links, SideBar, BlogSettings


# 文章表单类
class ArticleForm(forms.ModelForm):
    # 可以在这里添加自定义字段，例如使用Markdown编辑器
    # body = forms.CharField(widget=AdminPagedownWidget())

    class Meta:
        model = Article
        fields = '__all__'  # 包含所有模型字段


# 管理动作：将选中的文章状态改为发布
def makr_article_publish(modeladmin, request, queryset):
    queryset.update(status='p')  # 'p' 代表已发布状态


# 管理动作：将选中的文章状态改为草稿
def draft_article(modeladmin, request, queryset):
    queryset.update(status='d')  # 'd' 代表草稿状态


# 管理动作：关闭选中文章的评论功能
def close_article_commentstatus(modeladmin, request, queryset):
    queryset.update(comment_status='c')  # 'c' 代表评论关闭


# 管理动作：开启选中文章的评论功能
def open_article_commentstatus(modeladmin, request, queryset):
    queryset.update(comment_status='o')  # 'o' 代表评论开启


# 为管理动作设置显示名称
makr_article_publish.short_description = _('Publish selected articles')
draft_article.short_description = _('Draft selected articles')
close_article_commentstatus.short_description = _('Close article comments')
open_article_commentstatus.short_description = _('Open article comments')


# 文章管理类
class ArticlelAdmin(admin.ModelAdmin):
    list_per_page = 20  # 每页显示20条记录
    search_fields = ('body', 'title')  # 可搜索的字段
    form = ArticleForm  # 使用自定义表单
    list_display = (
        'id',
        'title',
        'author',
        'link_to_category',  # 自定义方法显示分类链接
        'creation_time',
        'views',
        'status',
        'type',
        'article_order')  # 列表页显示的字段
    list_display_links = ('id', 'title')  # 可点击链接的字段
    list_filter = ('status', 'type', 'category')  # 右侧过滤器
    date_hierarchy = 'creation_time'  # 按时间分层导航
    filter_horizontal = ('tags',)  # 水平多对多选择器
    exclude = ('creation_time', 'last_modify_time')  # 排除的表单字段
    view_on_site = True  # 显示"在站点查看"按钮
    actions = [
        makr_article_publish,
        draft_article,
        close_article_commentstatus,
        open_article_commentstatus]  # 可用的管理动作
    raw_id_fields = ('author', 'category',)  # 使用原始ID字段（显示搜索框）

    # 自定义方法：显示分类链接
    def link_to_category(self, obj):
        info = (obj.category._meta.app_label, obj.category._meta.model_name)
        link = reverse('admin:%s_%s_change' % info, args=(obj.category.id,))
        return format_html(u'<a href="%s">%s</a>' % (link, obj.category.name))

    link_to_category.short_description = _('category')  # 设置列标题

    # 重写获取表单方法，限制作者只能选择超级用户
    def get_form(self, request, obj=None, **kwargs):
        form = super(ArticlelAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['author'].queryset = get_user_model(
        ).objects.filter(is_superuser=True)
        return form

    # 保存模型时的额外操作
    def save_model(self, request, obj, form, change):
        super(ArticlelAdmin, self).save_model(request, obj, form, change)

    # 获取"在站点查看"的URL
    def get_view_on_site_url(self, obj=None):
        if obj:
            url = obj.get_full_url()  # 获取文章的完整URL
            return url
        else:
            from djangoblog.utils import get_current_site
            site = get_current_site().domain  # 获取当前站点域名
            return site


# 标签管理类
class TagAdmin(admin.ModelAdmin):
    exclude = ('slug', 'last_mod_time', 'creation_time')  # 排除自动生成的字段


# 分类管理类
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent_category', 'index')  # 列表页显示的字段
    exclude = ('slug', 'last_mod_time', 'creation_time')  # 排除自动生成的字段


# 链接管理类
class LinksAdmin(admin.ModelAdmin):
    exclude = ('last_mod_time', 'creation_time')  # 排除时间字段


# 侧边栏管理类
class SideBarAdmin(admin.ModelAdmin):
    list_display = ('name', 'content', 'is_enable', 'sequence')  # 列表页显示的字段
    exclude = ('last_mod_time', 'creation_time')  # 排除时间字段


# 博客设置管理类
class BlogSettingsAdmin(admin.ModelAdmin):
    pass  # 使用默认管理选项
