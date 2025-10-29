import logging
import re
from abc import abstractmethod

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from mdeditor.fields import MDTextField
from uuslug import slugify

from djangoblog.utils import cache_decorator, cache
from djangoblog.utils import get_current_site

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)


# 链接显示类型选择枚举
class LinkShowType(models.TextChoices):
    I = ('i', _('index'))  # 首页显示
    L = ('l', _('list'))   # 列表页显示
    P = ('p', _('post'))   # 文章页显示
    A = ('a', _('all'))    # 所有页面显示
    S = ('s', _('slide'))  # 幻灯片显示


# 基础模型抽象类，提供公共字段和方法
class BaseModel(models.Model):
    id = models.AutoField(primary_key=True)  # 自增主键
    creation_time = models.DateTimeField(_('creation time'), default=now)  # 创建时间
    last_modify_time = models.DateTimeField(_('modify time'), default=now)  # 最后修改时间

    def save(self, *args, **kwargs):
        # 检查是否是更新文章浏览量的操作
        is_update_views = isinstance(
            self,
            Article) and 'update_fields' in kwargs and kwargs['update_fields'] == ['views']
        if is_update_views:
            # 如果是更新浏览量，直接使用update方法提高性能
            Article.objects.filter(pk=self.pk).update(views=self.views)
        else:
            # 如果有slug字段，自动从title或name生成slug
            if 'slug' in self.__dict__:
                slug = getattr(
                    self, 'title') if 'title' in self.__dict__ else getattr(
                    self, 'name')
                setattr(self, 'slug', slugify(slug))
            # 调用父类的save方法
            super().save(*args, **kwargs)

    def get_full_url(self):
        # 获取完整的URL（包含域名）
        site = get_current_site().domain
        url = "https://{site}{path}".format(site=site,
                                            path=self.get_absolute_url())
        return url

    class Meta:
        abstract = True  # 这是一个抽象基类，不会创建数据库表

    @abstractmethod
    def get_absolute_url(self):
        # 抽象方法，子类必须实现，用于获取对象的绝对URL
        pass


# 文章模型
class Article(BaseModel):
    """文章模型"""
    # 状态选择
    STATUS_CHOICES = (
        ('d', _('Draft')),     # 草稿
        ('p', _('Published')), # 已发布
    )
    # 评论状态选择
    COMMENT_STATUS = (
        ('o', _('Open')),   # 开放评论
        ('c', _('Close')),  # 关闭评论
    )
    # 类型选择
    TYPE = (
        ('a', _('Article')),  # 文章
        ('p', _('Page')),     # 页面
    )
    
    title = models.CharField(_('title'), max_length=200, unique=True)  # 标题，唯一
    body = MDTextField(_('body'))  # 正文，使用Markdown编辑器
    pub_time = models.DateTimeField(
        _('publish time'), blank=False, null=False, default=now)  # 发布时间
    status = models.CharField(
        _('status'),
        max_length=1,
        choices=STATUS_CHOICES,
        default='p')  # 状态，默认为已发布
    comment_status = models.CharField(
        _('comment status'),
        max_length=1,
        choices=COMMENT_STATUS,
        default='o')  # 评论状态，默认为开放
    type = models.CharField(_('type'), max_length=1, choices=TYPE, default='a')  # 类型，默认为文章
    views = models.PositiveIntegerField(_('views'), default=0)  # 浏览量
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('author'),
        blank=False,
        null=False,
        on_delete=models.CASCADE)  # 作者，关联用户模型
    article_order = models.IntegerField(
        _('order'), blank=False, null=False, default=0)  # 文章排序
    show_toc = models.BooleanField(_('show toc'), blank=False, null=False, default=False)  # 是否显示目录
    category = models.ForeignKey(
        'Category',
        verbose_name=_('category'),
        on_delete=models.CASCADE,
        blank=False,
        null=False)  # 分类，关联分类模型
    tags = models.ManyToManyField('Tag', verbose_name=_('tag'), blank=True)  # 标签，多对多关系

    def body_to_string(self):
        # 返回正文内容的字符串表示
        return self.body

    def __str__(self):
        # 对象的字符串表示
        return self.title

    class Meta:
        ordering = ['-article_order', '-pub_time']  # 默认按排序和发布时间降序排列
        verbose_name = _('article')  # 单数名称
        verbose_name_plural = verbose_name  # 复数名称
        get_latest_by = 'id'  # 获取最新记录的依据字段

    def get_absolute_url(self):
        # 获取文章的绝对URL
        return reverse('blog:detailbyid', kwargs={
            'article_id': self.id,
            'year': self.creation_time.year,
            'month': self.creation_time.month,
            'day': self.creation_time.day
        })

    @cache_decorator(60 * 60 * 10)  # 缓存10小时
    def get_category_tree(self):
        # 获取分类树
        tree = self.category.get_category_tree()
        names = list(map(lambda c: (c.name, c.get_absolute_url()), tree))

        return names

    def save(self, *args, **kwargs):
        # 保存文章，调用父类的save方法
        super().save(*args, **kwargs)

    def viewed(self):
        # 增加文章浏览量
        self.views += 1
        self.save(update_fields=['views'])

    def comment_list(self):
        # 获取文章的评论列表，使用缓存
        cache_key = 'article_comments_{id}'.format(id=self.id)
        value = cache.get(cache_key)
        if value:
            logger.info('get article comments:{id}'.format(id=self.id))
            return value
        else:
            comments = self.comment_set.filter(is_enable=True).order_by('-id')
            cache.set(cache_key, comments, 60 * 100)  # 缓存100分钟
            logger.info('set article comments:{id}'.format(id=self.id))
            return comments

    def get_admin_url(self):
        # 获取文章在管理后台的URL
        info = (self._meta.app_label, self._meta.model_name)
        return reverse('admin:%s_%s_change' % info, args=(self.pk,))

    @cache_decorator(expiration=60 * 100)  # 缓存100分钟
    def next_article(self):
        # 获取下一篇文章
        return Article.objects.filter(
            id__gt=self.id, status='p').order_by('id').first()

    @cache_decorator(expiration=60 * 100)  # 缓存100分钟
    def prev_article(self):
        # 获取上一篇文章
        return Article.objects.filter(id__lt=self.id, status='p').first()

    def get_first_image_url(self):
        """
        从文章正文中提取第一张图片的URL
        :return: 图片URL或空字符串
        """
        match = re.search(r'!\[.*?\]\((.+?)\)', self.body)
        if match:
            return match.group(1)
        return ""


# 分类模型
class Category(BaseModel):
    """文章分类模型"""
    name = models.CharField(_('category name'), max_length=30, unique=True)  # 分类名称，唯一
    parent_category = models.ForeignKey(
        'self',
        verbose_name=_('parent category'),
        blank=True,
        null=True,
        on_delete=models.CASCADE)  # 父分类，自关联
    slug = models.SlugField(default='no-slug', max_length=60, blank=True)  # URL别名
    index = models.IntegerField(default=0, verbose_name=_('index'))  # 排序索引

    class Meta:
        ordering = ['-index']  # 按索引降序排列
        verbose_name = _('category')  # 单数名称
        verbose_name_plural = verbose_name  # 复数名称

    def get_absolute_url(self):
        # 获取分类的绝对URL
        return reverse(
            'blog:category_detail', kwargs={
                'category_name': self.slug})

    def __str__(self):
        # 对象的字符串表示
        return self.name

    @cache_decorator(60 * 60 * 10)  # 缓存10小时
    def get_category_tree(self):
        """
        递归获得分类目录的父级
        :return: 分类树列表
        """
        categorys = []

        def parse(category):
            categorys.append(category)
            if category.parent_category:
                parse(category.parent_category)

        parse(self)
        return categorys

    @cache_decorator(60 * 60 * 10)  # 缓存10小时
    def get_sub_categorys(self):
        """
        获得当前分类目录所有子集
        :return: 子分类列表
        """
        categorys = []
        all_categorys = Category.objects.all()

        def parse(category):
            if category not in categorys:
                categorys.append(category)
            childs = all_categorys.filter(parent_category=category)
            for child in childs:
                if category not in categorys:
                    categorys.append(child)
                parse(child)

        parse(self)
        return categorys


# 标签模型
class Tag(BaseModel):
    """文章标签模型"""
    name = models.CharField(_('tag name'), max_length=30, unique=True)  # 标签名称，唯一
    slug = models.SlugField(default='no-slug', max_length=60, blank=True)  # URL别名

    def __str__(self):
        # 对象的字符串表示
        return self.name

    def get_absolute_url(self):
        # 获取标签的绝对URL
        return reverse('blog:tag_detail', kwargs={'tag_name': self.slug})

    @cache_decorator(60 * 60 * 10)  # 缓存10小时
    def get_article_count(self):
        # 获取使用该标签的文章数量
        return Article.objects.filter(tags__name=self.name).distinct().count()

    class Meta:
        ordering = ['name']  # 按名称排序
        verbose_name = _('tag')  # 单数名称
        verbose_name_plural = verbose_name  # 复数名称


# 友情链接模型
class Links(models.Model):
    """友情链接模型"""

    name = models.CharField(_('link name'), max_length=30, unique=True)  # 链接名称，唯一
    link = models.URLField(_('link'))  # 链接URL
    sequence = models.IntegerField(_('order'), unique=True)  # 排序，唯一
    is_enable = models.BooleanField(
        _('is show'), default=True, blank=False, null=False)  # 是否启用
    show_type = models.CharField(
        _('show type'),
        max_length=1,
        choices=LinkShowType.choices,
        default=LinkShowType.I)  # 显示类型
    creation_time = models.DateTimeField(_('creation time'), default=now)  # 创建时间
    last_mod_time = models.DateTimeField(_('modify time'), default=now)  # 最后修改时间

    class Meta:
        ordering = ['sequence']  # 按排序字段排序
        verbose_name = _('link')  # 单数名称
        verbose_name_plural = verbose_name  # 复数名称

    def __str__(self):
        # 对象的字符串表示
        return self.name


# 侧边栏模型
class SideBar(models.Model):
    """侧边栏模型，可以展示一些html内容"""
    name = models.CharField(_('title'), max_length=100)  # 标题
    content = models.TextField(_('content'))  # 内容
    sequence = models.IntegerField(_('order'), unique=True)  # 排序，唯一
    is_enable = models.BooleanField(_('is enable'), default=True)  # 是否启用
    creation_time = models.DateTimeField(_('creation time'), default=now)  # 创建时间
    last_mod_time = models.DateTimeField(_('modify time'), default=now)  # 最后修改时间

    class Meta:
        ordering = ['sequence']  # 按排序字段排序
        verbose_name = _('sidebar')  # 单数名称
        verbose_name_plural = verbose_name  # 复数名称

    def __str__(self):
        # 对象的字符串表示
        return self.name


# 博客设置模型
class BlogSettings(models.Model):
    """博客配置模型"""
    site_name = models.CharField(
        _('site name'),
        max_length=200,
        null=False,
        blank=False,
        default='')  # 网站名称
    site_description = models.TextField(
        _('site description'),
        max_length=1000,
        null=False,
        blank=False,
        default='')  # 网站描述
    site_seo_description = models.TextField(
        _('site seo description'), max_length=1000, null=False, blank=False, default='')  # SEO描述
    site_keywords = models.TextField(
        _('site keywords'),
        max_length=1000,
        null=False,
        blank=False,
        default='')  # 网站关键词
    article_sub_length = models.IntegerField(_('article sub length'), default=300)  # 文章摘要长度
    sidebar_article_count = models.IntegerField(_('sidebar article count'), default=10)  # 侧边栏文章数量
    sidebar_comment_count = models.IntegerField(_('sidebar comment count'), default=5)  # 侧边栏评论数量
    article_comment_count = models.IntegerField(_('article comment count'), default=5)  # 文章评论数量
    show_google_adsense = models.BooleanField(_('show adsense'), default=False)  # 是否显示Google广告
    google_adsense_codes = models.TextField(
        _('adsense code'), max_length=2000, null=True, blank=True, default='')  # 广告代码
    open_site_comment = models.BooleanField(_('open site comment'), default=True)  # 是否开启全站评论
    global_header = models.TextField("公共头部", null=True, blank=True, default='')  # 公共头部HTML
    global_footer = models.TextField("公共尾部", null=True, blank=True, default='')  # 公共尾部HTML
    beian_code = models.CharField(
        '备案号',
        max_length=2000,
        null=True,
        blank=True,
        default='')  # 备案号
    analytics_code = models.TextField(
        "网站统计代码",
        max_length=1000,
        null=False,
        blank=False,
        default='')  # 网站统计代码
    show_gongan_code = models.BooleanField(
        '是否显示公安备案号', default=False, null=False)  # 是否显示公安备案号
    gongan_beiancode = models.TextField(
        '公安备案号',
        max_length=2000,
        null=True,
        blank=True,
        default='')  # 公安备案号
    comment_need_review = models.BooleanField(
        '评论是否需要审核', default=False, null=False)  # 评论是否需要审核

    class Meta:
        verbose_name = _('Website configuration')  # 单数名称
        verbose_name_plural = verbose_name  # 复数名称

    def __str__(self):
        # 对象的字符串表示
        return self.site_name

    def clean(self):
        # 验证方法，确保只能有一个配置实例
        if BlogSettings.objects.exclude(id=self.id).count():
            raise ValidationError(_('There can only be one configuration'))

    def save(self, *args, **kwargs):
        # 保存配置，保存后清除缓存
        super().save(*args, **kwargs)
        from djangoblog.utils import cache
        cache.clear()  # 清除所有缓存
