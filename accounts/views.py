# 导入日志模块
import logging
# 导入国际化翻译
from django.utils.translation import gettext_lazy as _
# 导入Django配置
from django.conf import settings
# 导入Django认证相关模块
from django.contrib import auth
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import get_user_model
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
# 导入HTTP响应类
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.http.request import HttpRequest
from django.http.response import HttpResponse
# 导入快捷函数
from django.shortcuts import get_object_or_404
from django.shortcuts import render
# 导入URL反向解析
from django.urls import reverse
# 导入方法装饰器
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
# 导入视图基类
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import FormView, RedirectView

# 导入自定义工具函数
from djangoblog.utils import send_email, get_sha256, get_current_site, generate_code, delete_sidebar_cache
# 导入当前应用的工具模块
from . import utils
# 导入自定义表单
from .forms import RegisterForm, LoginForm, ForgetPasswordForm, ForgetPasswordCodeForm
# 导入用户模型
from .models import BlogUser

# 获取日志器
logger = logging.getLogger(__name__)


# 视图类注释
# Create your views here.

class RegisterView(FormView):
    """
    用户注册视图
    处理用户注册流程，包括表单验证、用户创建、邮箱验证发送等
    """
    form_class = RegisterForm  # 使用自定义注册表单
    template_name = 'account/registration_form.html'  # 注册模板

    @method_decorator(csrf_protect)  # CSRF保护，防止跨站请求伪造
    def dispatch(self, *args, **kwargs):
        return super(RegisterView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        """
        表单验证通过后的处理逻辑
        """
        if form.is_valid():
            # 保存用户但不提交到数据库（commit=False）
            user = form.save(False)
            user.is_active = False  # 设置用户为未激活状态，需要邮箱验证
            user.source = 'Register'  # 记录用户来源
            user.save(True)  # 保存用户到数据库
            
            # 获取当前站点信息
            site = get_current_site().domain
            # 生成邮箱验证签名，用于安全验证
            sign = get_sha256(get_sha256(settings.SECRET_KEY + str(user.id)))

            # 调试模式下使用本地地址
            if settings.DEBUG:
                site = '127.0.0.1:8000'
                
            # 构建验证URL
            path = reverse('account:result')
            url = "http://{site}{path}?type=validation&id={id}&sign={sign}".format(
                site=site, path=path, id=user.id, sign=sign)

            # 构建邮件内容
            content = """
                            <p>请点击下面链接验证您的邮箱</p>

                            <a href="{url}" rel="bookmark">{url}</a>

                            再次感谢您！
                            <br />
                            如果上面链接无法打开，请将此链接复制至浏览器。
                            {url}
                            """.format(url=url)
            # 发送验证邮件
            send_email(
                emailto=[
                    user.email,
                ],
                title='验证您的电子邮箱',
                content=content)

            # 重定向到结果页面
            url = reverse('accounts:result') + \
                  '?type=register&id=' + str(user.id)
            return HttpResponseRedirect(url)
        else:
            # 表单验证失败，重新渲染表单页
            return self.render_to_response({
                'form': form
            })


class LogoutView(RedirectView):
    """
    用户退出登录视图
    处理用户退出登录，清理会话和缓存
    """
    url = '/login/'  # 退出后重定向到登录页

    @method_decorator(never_cache)  # 禁止缓存，确保每次都是最新状态
    def dispatch(self, request, *args, **kwargs):
        return super(LogoutView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        处理GET请求，执行退出登录操作
        """
        logout(request)  # Django内置退出函数
        delete_sidebar_cache()  # 清理侧边栏缓存
        return super(LogoutView, self).get(request, *args, **kwargs)


class LoginView(FormView):
    """
    用户登录视图
    处理用户登录认证，支持记住登录状态
    """
    form_class = LoginForm  # 使用自定义登录表单
    template_name = 'account/login.html'  # 登录模板
    success_url = '/'  # 登录成功默认重定向到首页
    redirect_field_name = REDIRECT_FIELD_NAME  # 重定向字段名
    login_ttl = 2626560  # 一个月的时间（秒），用于记住登录状态

    # 多个安全装饰器
    @method_decorator(sensitive_post_parameters('password'))  # 敏感参数保护
    @method_decorator(csrf_protect)  # CSRF保护
    @method_decorator(never_cache)  # 禁止缓存
    def dispatch(self, request, *args, **kwargs):
        return super(LoginView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        添加上下文数据，处理重定向逻辑
        """
        redirect_to = self.request.GET.get(self.redirect_field_name)
        if redirect_to is None:
            redirect_to = '/'  # 默认重定向到首页
        kwargs['redirect_to'] = redirect_to

        return super(LoginView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        """
        表单验证通过后的处理逻辑
        """
        form = AuthenticationForm(data=self.request.POST, request=self.request)

        if form.is_valid():
            # 清理侧边栏缓存
            delete_sidebar_cache()
            logger.info(self.redirect_field_name)

            # 执行登录操作
            auth.login(self.request, form.get_user())
            
            # 处理"记住我"功能
            if self.request.POST.get("remember"):
                self.request.session.set_expiry(self.login_ttl)  # 设置会话过期时间
                
            return super(LoginView, self).form_valid(form)
        else:
            # 登录失败，重新渲染登录页
            return self.render_to_response({
                'form': form
            })

    def get_success_url(self):
        """
        获取登录成功后的重定向URL
        安全检查，防止开放重定向攻击
        """
        redirect_to = self.request.POST.get(self.redirect_field_name)
        # 验证重定向URL的安全性
        if not url_has_allowed_host_and_scheme(
                url=redirect_to, allowed_hosts=[
                    self.request.get_host()]):
            redirect_to = self.success_url  # 不安全的URL使用默认URL
        return redirect_to


def account_result(request):
    """
    账户操作结果页面
    显示注册结果或处理邮箱验证
    """
    type = request.GET.get('type')  # 操作类型
    id = request.GET.get('id')  # 用户ID

    # 获取用户对象，不存在则返回404
    user = get_object_or_404(get_user_model(), id=id)
    logger.info(type)
    
    # 如果用户已激活，直接重定向到首页
    if user.is_active:
        return HttpResponseRedirect('/')
        
    # 处理注册和验证逻辑
    if type and type in ['register', 'validation']:
        if type == 'register':
            # 注册成功页面
            content = '''
    恭喜您注册成功，一封验证邮件已经发送到您的邮箱，请验证您的邮箱后登录本站。
    '''
            title = '注册成功'
        else:
            # 邮箱验证逻辑
            c_sign = get_sha256(get_sha256(settings.SECRET_KEY + str(user.id)))
            sign = request.GET.get('sign')
            # 验证签名，防止篡改
            if sign != c_sign:
                return HttpResponseForbidden()  # 签名不匹配，返回403
            # 激活用户账户
            user.is_active = True
            user.save()
            content = '''
            恭喜您已经成功的完成邮箱验证，您现在可以使用您的账号来登录本站。
            '''
            title = '验证成功'
        # 渲染结果页面
        return render(request, 'account/result.html', {
            'title': title,
            'content': content
        })
    else:
        # 无效的操作类型，重定向到首页
        return HttpResponseRedirect('/')


class ForgetPasswordView(FormView):
    """
    忘记密码视图
    处理密码重置逻辑
    """
    form_class = ForgetPasswordForm  # 使用忘记密码表单
    template_name = 'account/forget_password.html'  # 模板

    def form_valid(self, form):
        """
        表单验证通过后的处理逻辑
        """
        if form.is_valid():
            # 根据邮箱查找用户
            blog_user = BlogUser.objects.filter(email=form.cleaned_data.get("email")).get()
            # 使用新密码（自动加密）
            blog_user.password = make_password(form.cleaned_data["new_password2"])
            blog_user.save()  # 保存用户
            return HttpResponseRedirect('/login/')  # 重定向到登录页
        else:
            # 表单验证失败，重新渲染表单
            return self.render_to_response({'form': form})


class ForgetPasswordEmailCode(View):
    """
    发送忘记密码验证码视图
    处理验证码的生成和发送
    """

    def post(self, request: HttpRequest):
        """
        处理POST请求，发送验证码邮件
        """
        form = ForgetPasswordCodeForm(request.POST)
        if not form.is_valid():
            return HttpResponse("错误的邮箱")  # 表单验证失败
            
        to_email = form.cleaned_data["email"]

        # 生成验证码
        code = generate_code()
        # 发送验证邮件
        utils.send_verify_email(to_email, code)
        # 存储验证码到缓存
        utils.set_code(to_email, code)

        return HttpResponse("ok")  # 返回成功响应
