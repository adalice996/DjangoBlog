# 导入Django内置的抽象用户基类
from django.contrib.auth.models import AbstractUser
# 导入Django的数据库模型
from django.db import models
# 导入URL反向解析函数
from django.urls import reverse
# 导入当前时间函数
from django.utils.timezone import now
# 导入国际化翻译函数
from django.utils.translation import gettext_lazy as _
# 导入自定义工具函数，用于获取当前站点信息
from djangoblog.utils import get_current_site


# 模型定义注释
# Create your models here.

class BlogUser(AbstractUser):
    """
    自定义博客用户模型
    继承自Django的AbstractUser，扩展了博客系统需要的用户字段
    
    这个模型替换了Django默认的用户模型，提供了：
    - 所有标准用户认证功能
    - 博客特定的用户信息字段
    - 用户相关的URL生成方法
    """
    
    # 昵称字段：用户的显示名称，可选字段
    nickname = models.CharField(
        _('nick name'),      # 字段标签，支持国际化翻译
        max_length=100,      # 最大长度100字符
        blank=True           # 允许为空，不是必填字段
    )
    
    # 创建时间：记录用户账户创建的时间
    creation_time = models.DateTimeField(
        _('creation time'),  # 字段标签
        default=now          # 默认值为当前时间
    )
    
    # 最后修改时间：记录用户信息最后修改的时间
    last_modify_time = models.DateTimeField(
        _('last modify time'),  # 字段标签
        default=now             # 默认值为当前时间
    )
    
    # 创建来源：记录用户是通过什么渠道注册的
    source = models.CharField(
        _('create source'),  # 字段标签
        max_length=100,      # 最大长度100字符
        blank=True           # 允许为空
    )

    def get_absolute_url(self):
        """
        获取用户的绝对URL（相对路径）
        用于Django admin、模板等需要用户详情页URL的地方
        
        Returns:
            str: 用户详情页的URL路径
        """
        return reverse(
            'blog:author_detail',  # URL配置的名称，在blog应用的urls.py中定义
            kwargs={
                'author_name': self.username  # URL参数，使用用户名作为标识
            })

    def __str__(self):
        """
        定义模型的字符串表示
        在Django admin、shell等地方显示为用户的邮箱
        
        Returns:
            str: 用户的邮箱地址
        """
        return self.email

    def get_full_url(self):
        """
        获取用户的完整URL（包含域名）
        用于生成可以在外部访问的完整用户链接
        
        Returns:
            str: 包含域名的完整用户URL
        """
        # 获取当前站点的域名
        site = get_current_site().domain
        # 生成完整的URL，包含https协议和域名
        url = "https://{site}{path}".format(
            site=site,
            path=self.get_absolute_url()  # 使用get_absolute_url获取路径部分
        )
        return url

    class Meta:
        """
        模型的元数据配置
        定义模型在数据库和Django admin中的行为
        """
        
        # 默认排序规则：按ID倒序排列，新的用户显示在前面
        ordering = ['-id']
        
        # 在Django admin中显示的单数名称
        verbose_name = _('user')
        
        # 在Django admin中显示的复数名称（与单数相同）
        verbose_name_plural = verbose_name
        
        # 指定获取最新记录的字段（用于get_latest()方法）
        get_latest_by = 'id'
