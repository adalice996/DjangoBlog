# 导入Django的URL路径函数
from django.urls import path
from django.urls import re_path  # 正则表达式路径，用于更灵活的URL匹配

# 导入当前应用的视图模块
from . import views
# 导入自定义登录表单
from .forms import LoginForm

# 定义应用的命名空间，用于URL反向解析时区分不同应用的URL
app_name = "accounts"

# 定义URL模式列表，将URL路径映射到相应的视图函数或类
urlpatterns = [
    # 登录URL
    re_path(r'^login/$',  # 正则表达式匹配以 login/ 结尾的URL
            # 使用类视图，设置登录成功后的重定向URL为首页
            views.LoginView.as_view(success_url='/'),
            name='login',  # URL名称，用于反向解析
            # 传递额外参数，指定使用自定义的登录表单
            kwargs={'authentication_form': LoginForm}),
    
    # 注册URL
    re_path(r'^register/$',  # 匹配以 register/ 结尾的URL
            # 使用类视图，设置注册成功后的重定向URL为首页
            views.RegisterView.as_view(success_url="/"),
            name='register'),  # URL名称为register
    
    # 退出登录URL
    re_path(r'^logout/$',  # 匹配以 logout/ 结尾的URL
            # 使用类视图，不需要设置成功URL（通常重定向到登录页或首页）
            views.LogoutView.as_view(),
            name='logout'),  # URL名称为logout
    
    # 账户操作结果页面URL（使用path函数，更简洁的路径匹配）
    path(r'account/result.html',  # 精确匹配 account/result.html 路径
         # 使用函数视图显示账户操作结果页面
         views.account_result,
         name='result'),  # URL名称为result
    
    # 忘记密码页面URL
    re_path(r'^forget_password/$',  # 匹配以 forget_password/ 结尾的URL
            # 使用类视图处理忘记密码逻辑
            views.ForgetPasswordView.as_view(),
            name='forget_password'),  # URL名称为forget_password
    
    # 获取忘记密码验证码URL
    re_path(r'^forget_password_code/$',  # 匹配以 forget_password_code/ 结尾的URL
            # 使用类视图处理验证码发送逻辑
            views.ForgetPasswordEmailCode.as_view(),
            name='forget_password_code'),  # URL名称为forget_password_code
]
