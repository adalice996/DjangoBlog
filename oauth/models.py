# Create your models here.
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _


class OAuthUser(models.Model):
    """
    OAuth用户模型
    用于存储通过第三方OAuth登录的用户信息
    """
    
    # 关联到本站用户，如果用户绑定了本地账户则不为空
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # 使用Django认证系统的用户模型
        verbose_name=_('author'),  # 国际化标签
        blank=True,
        null=True,
        on_delete=models.CASCADE)  # 关联用户删除时级联删除
    
    # 第三方平台的用户唯一标识
    openid = models.CharField(max_length=50)
    
    # 用户在第三方平台的昵称
    nickname = models.CharField(max_length=50, verbose_name=_('nick name'))
    
    # OAuth访问令牌，用于调用第三方API
    token = models.CharField(max_length=150, null=True, blank=True)
    
    # 用户在第三方平台的头像URL
    picture = models.CharField(max_length=350, blank=True, null=True)
    
    # OAuth服务商类型（如github、weibo等）
    type = models.CharField(blank=False, null=False, max_length=50)
    
    # 用户在第三方平台的邮箱地址
    email = models.CharField(max_length=50, null=True, blank=True)
    
    # 存储额外的用户元数据，通常是JSON格式
    metadata = models.TextField(null=True, blank=True)
    
    # 记录创建时间，默认为当前时间
    creation_time = models.DateTimeField(_('creation time'), default=now)
    
    # 记录最后修改时间，默认为当前时间
    last_modify_time = models.DateTimeField(_('last modify time'), default=now)

    def __str__(self):
        """
        在Admin和其他地方显示的对象字符串表示
        """
        return self.nickname

    class Meta:
        # 在Admin中显示的单数名称
        verbose_name = _('oauth user')
        # 在Admin中显示的复数名称
        verbose_name_plural = verbose_name
        # 默认按创建时间降序排列
        ordering = ['-creation_time']


class OAuthConfig(models.Model):
    """
    OAuth配置模型
    用于存储不同第三方OAuth服务的配置信息
    """
    
    # OAuth服务商类型选项
    TYPE = (
        ('weibo', _('weibo')),      # 微博
        ('google', _('google')),    # 谷歌
        ('github', 'GitHub'),       # GitHub
        ('facebook', 'FaceBook'),   # Facebook
        ('qq', 'QQ'),               # QQ
    )
    
    # OAuth服务商类型
    type = models.CharField(_('type'), max_length=10, choices=TYPE, default='a')
    
    # 第三方应用的应用密钥
    appkey = models.CharField(max_length=200, verbose_name='AppKey')
    
    # 第三方应用的应用密钥（保密）
    appsecret = models.CharField(max_length=200, verbose_name='AppSecret')
    
    # OAuth认证成功后的回调地址
    callback_url = models.CharField(
        max_length=200,
        verbose_name=_('callback url'),
        blank=False,
        default='')
    
    # 是否启用该OAuth配置
    is_enable = models.BooleanField(
        _('is enable'), default=True, blank=False, null=False)
    
    # 记录创建时间，默认为当前时间
    creation_time = models.DateTimeField(_('creation time'), default=now)
    
    # 记录最后修改时间，默认为当前时间
    last_modify_time = models.DateTimeField(_('last modify time'), default=now)

    def clean(self):
        """
        模型验证方法，确保同类型的OAuth配置只有一个
        """
        # 检查是否已存在同类型的配置（排除自身）
        if OAuthConfig.objects.filter(
                type=self.type).exclude(id=self.id).count():
            raise ValidationError(_(self.type + _('already exists')))

    def __str__(self):
        """
        在Admin和其他地方显示的对象字符串表示
        """
        return self.type

    class Meta:
        # 在Admin中显示的中文名称
        verbose_name = 'oauth配置'
        verbose_name_plural = verbose_name
        # 默认按创建时间降序排列
        ordering = ['-creation_time']
