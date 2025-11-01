import logging
# Create your views here.
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from djangoblog.blog_signals import oauth_user_login_signal
from djangoblog.utils import get_current_site
from djangoblog.utils import send_email, get_sha256
from oauth.forms import RequireEmailForm
from .models import OAuthUser
from .oauthmanager import get_manager_by_type, OAuthAccessTokenException

# 获取日志记录器
logger = logging.getLogger(__name__)


def get_redirecturl(request):
    """
    获取安全的重定向URL
    
    功能：
    - 从请求参数中获取next_url
    - 验证URL安全性，防止开放重定向漏洞
    - 处理特殊情况（如登录页面）
    
    Returns:
        安全的内部重定向URL
    """
    nexturl = request.GET.get('next_url', None)
    
    # 处理登录页面的特殊情况
    if not nexturl or nexturl == '/login/' or nexturl == '/login':
        nexturl = '/'
        return nexturl
    
    # 验证URL安全性，防止跨站重定向
    p = urlparse(nexturl)
    if p.netloc:  # 如果URL包含域名
        site = get_current_site().domain
        # 比较域名，确保重定向到本站
        if not p.netloc.replace('www.', '') == site.replace('www.', ''):
            logger.info('非法url:' + nexturl)
            return "/"  # 非法URL重定向到首页
    return nexturl


def oauthlogin(request):
    """
    OAuth登录入口视图
    
    功能：
    - 根据type参数选择对应的OAuth管理器
    - 重定向到第三方平台的授权页面
    """
    type = request.GET.get('type', None)
    if not type:
        return HttpResponseRedirect('/')
    
    # 获取对应的OAuth管理器
    manager = get_manager_by_type(type)
    if not manager:
        return HttpResponseRedirect('/')
    
    # 获取安全的重定向URL并生成授权URL
    nexturl = get_redirecturl(request)
    authorizeurl = manager.get_authorization_url(nexturl)
    return HttpResponseRedirect(authorizeurl)


def authorize(request):
    """
    OAuth授权回调处理视图
    
    功能：
    - 处理第三方平台回调的授权码
    - 获取用户信息并创建/更新本地用户
    - 处理登录或邮箱补充流程
    """
    type = request.GET.get('type', None)
    if not type:
        return HttpResponseRedirect('/')
    
    manager = get_manager_by_type(type)
    if not manager:
        return HttpResponseRedirect('/')
    
    # 获取授权码
    code = request.GET.get('code', None)
    try:
        # 使用授权码获取access token
        rsp = manager.get_access_token_by_code(code)
    except OAuthAccessTokenException as e:
        logger.warning("OAuthAccessTokenException:" + str(e))
        return HttpResponseRedirect('/')
    except Exception as e:
        logger.error(e)
        rsp = None
    
    nexturl = get_redirecturl(request)
    if not rsp:
        # 获取token失败，重新跳转到授权页面
        return HttpResponseRedirect(manager.get_authorization_url(nexturl))
    
    # 获取用户信息
    user = manager.get_oauth_userinfo()
    if user:
        # 处理昵称为空的情况
        if not user.nickname or not user.nickname.strip():
            user.nickname = "djangoblog" + timezone.now().strftime('%y%m%d%I%M%S')
        
        try:
            # 检查是否已存在该OAuth用户
            temp = OAuthUser.objects.get(type=type, openid=user.openid)
            # 更新用户信息
            temp.picture = user.picture
            temp.metadata = user.metadata
            temp.nickname = user.nickname
            user = temp
        except ObjectDoesNotExist:
            pass  # 新用户，继续处理
        
        # Facebook的token过长，特殊处理
        if type == 'facebook':
            user.token = ''
        
        # 如果OAuth返回了邮箱地址
        if user.email:
            with transaction.atomic():  # 使用事务保证数据一致性
                author = None
                try:
                    # 查找已关联的用户
                    author = get_user_model().objects.get(id=user.author_id)
                except ObjectDoesNotExist:
                    pass
                
                if not author:
                    # 根据邮箱查找或创建用户
                    result = get_user_model().objects.get_or_create(email=user.email)
                    author = result[0]
                    if result[1]:  # 如果是新创建的用户
                        try:
                            # 检查用户名是否已存在
                            get_user_model().objects.get(username=user.nickname)
                        except ObjectDoesNotExist:
                            author.username = user.nickname
                        else:
                            # 用户名冲突，生成唯一用户名
                            author.username = "djangoblog" + timezone.now().strftime('%y%m%d%I%M%S')
                        author.source = 'authorize'  # 标记用户来源
                        author.save()

                # 关联用户并保存
                user.author = author
                user.save()

                # 发送登录信号
                oauth_user_login_signal.send(
                    sender=authorize.__class__, id=user.id)
                
                # 登录用户
                login(request, author)
                return HttpResponseRedirect(nexturl)
        else:
            # 没有邮箱，需要用户补充
            user.save()
            url = reverse('oauth:require_email', kwargs={
                'oauthid': user.id
            })
            return HttpResponseRedirect(url)
    else:
        # 获取用户信息失败
        return HttpResponseRedirect(nexturl)


def emailconfirm(request, id, sign):
    """
    邮箱确认视图
    
    功能：
    - 验证邮箱确认链接的签名
    - 完成OAuth用户与本地用户的绑定
    - 发送绑定成功邮件
    """
    if not sign:
        return HttpResponseForbidden()
    
    # 验证签名安全性
    if not get_sha256(settings.SECRET_KEY +
                      str(id) +
                      settings.SECRET_KEY).upper() == sign.upper():
        return HttpResponseForbidden()
    
    oauthuser = get_object_or_404(OAuthUser, pk=id)
    
    with transaction.atomic():
        if oauthuser.author:
            # 已有关联用户，直接获取
            author = get_user_model().objects.get(pk=oauthuser.author_id)
        else:
            # 创建新用户
            result = get_user_model().objects.get_or_create(email=oauthuser.email)
            author = result[0]
            if result[1]:
                author.source = 'emailconfirm'
                # 处理用户名
                author.username = oauthuser.nickname.strip() if oauthuser.nickname.strip(
                ) else "djangoblog" + timezone.now().strftime('%y%m%d%I%M%S')
                author.save()
        
        # 完成绑定
        oauthuser.author = author
        oauthuser.save()
    
    # 发送登录信号并登录用户
    oauth_user_login_signal.send(
        sender=emailconfirm.__class__,
        id=oauthuser.id)
    login(request, author)

    # 发送绑定成功邮件
    site = 'http://' + get_current_site().domain
    content = _('''
     <p>Congratulations, you have successfully bound your email address. You can use
      %(oauthuser_type)s to directly log in to this website without a password.</p >
       You are welcome to continue to follow this site, the address is
        <a href=" " rel="bookmark">%(site)s</a >
            Thank you again!
            <br />
        If the link above cannot be opened, please copy this link to your browser.
        %(site)s
    ''') % {'oauthuser_type': oauthuser.type, 'site': site}

    send_email(emailto=[oauthuser.email, ], title=_('Congratulations on your successful binding!'), content=content)
    
    # 重定向到绑定成功页面
    url = reverse('oauth:bindsuccess', kwargs={
        'oauthid': id
    })
    url = url + '?type=success'
    return HttpResponseRedirect(url)


class RequireEmailView(FormView):
    """
    邮箱补充表单视图
    
    功能：
    - 显示邮箱补充表单
    - 处理邮箱提交
    - 发送邮箱确认邮件
    """
    form_class = RequireEmailForm
    template_name = 'oauth/require_email.html'

    def get(self, request, *args, **kwargs):
        """GET请求处理"""
        oauthid = self.kwargs['oauthid']
        oauthuser = get_object_or_404(OAuthUser, pk=oauthid)
        
        # 如果已有邮箱，直接跳过（理论上不会发生）
        if oauthuser.email:
            pass
        
        return super(RequireEmailView, self).get(request, *args, **kwargs)

    def get_initial(self):
        """设置表单初始值"""
        oauthid = self.kwargs['oauthid']
        return {
            'email': '',
            'oauthid': oauthid
        }

    def get_context_data(self, **kwargs):
        """添加上下文数据"""
        oauthid = self.kwargs['oauthid']
        oauthuser = get_object_or_404(OAuthUser, pk=oauthid)
        if oauthuser.picture:
            kwargs['picture'] = oauthuser.picture  # 显示用户头像
        return super(RequireEmailView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        """表单验证通过后的处理"""
        email = form.cleaned_data['email']
        oauthid = form.cleaned_data['oauthid']
        oauthuser = get_object_or_404(OAuthUser, pk=oauthid)
        oauthuser.email = email
        oauthuser.save()
        
        # 生成安全签名
        sign = get_sha256(settings.SECRET_KEY +
                          str(oauthuser.id) + settings.SECRET_KEY)
        
        # 构建确认链接
        site = get_current_site().domain
        if settings.DEBUG:
            site = '127.0.0.1:8000'  # 开发环境使用本地地址
            
        path = reverse('oauth:email_confirm', kwargs={
            'id': oauthid,
            'sign': sign
        })
        url = "http://{site}{path}".format(site=site, path=path)

        # 发送确认邮件
        content = _("""
               <p>Please click the link below to bind your email</p >

                 <a href="%(url)s" rel="bookmark">%(url)s</a >

                 Thank you again!
                 <br />
                 If the link above cannot be opened, please copy this link to your browser.
                  <br />
                 %(url)s
                """) % {'url': url}
        send_email(emailto=[email, ], title=_('Bind your email'), content=content)
        
        # 重定向到绑定成功提示页面
        url = reverse('oauth:bindsuccess', kwargs={
            'oauthid': oauthid
        })
        url = url + '?type=email'
        return HttpResponseRedirect(url)


def bindsuccess(request, oauthid):
    """
    绑定成功页面视图
    
    功能：
    - 显示绑定成功或等待确认的信息
    - 根据type参数显示不同的内容
    """
    type = request.GET.get('type', None)
    oauthuser = get_object_or_404(OAuthUser, pk=oauthid)
    
    if type == 'email':
        # 邮箱已提交，等待确认
        title = _('Bind your email')
        content = _(
            'Congratulations, the binding is just one step away. '
            'Please log in to your email to check the email to complete the binding. Thank you.')
    else:
        # 绑定已完成
        title = _('Binding successful')
        content = _(
            "Congratulations, you have successfully bound your email address. You can use %(oauthuser_type)s"
            " to directly log in to this website without a password. You are welcome to continue to follow this site." % {
                'oauthuser_type': oauthuser.type})
    
    return render(request, 'oauth/bindsuccess.html', {
        'title': title,
        'content': content
    })
