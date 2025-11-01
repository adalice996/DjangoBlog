from django.urls import path

from . import views

# 定义应用命名空间，用于URL反向解析时区分不同应用的URL
app_name = "oauth"

# OAuth认证系统的URL配置
urlpatterns = [
    # OAuth授权回调端点
    # 第三方OAuth服务商在用户授权后回调的URL
    path(
        r'oauth/authorize',
        views.authorize,  # 处理授权回调的视图函数
        name='authorize'  # 可选的URL名称，用于反向解析
    ),
    
    # 邮箱补充页面（当OAuth未返回邮箱时）
    # 参数: oauthid - OAuth用户的ID
    path(
        r'oauth/requireemail/<int:oauthid>.html',
        views.RequireEmailView.as_view(),  # 基于类的视图，处理邮箱补充表单
        name='require_email'  # URL名称，用于反向解析
    ),
    
    # 邮箱确认端点
    # 参数: id - OAuth用户ID, sign - 安全签名用于验证
    path(
        r'oauth/emailconfirm/<int:id>/<sign>.html',
        views.emailconfirm,  # 处理邮箱确认的视图函数
        name='email_confirm'  # URL名称，用于反向解析
    ),
    
    # 绑定成功页面
    # 参数: oauthid - OAuth用户的ID
    path(
        r'oauth/bindsuccess/<int:oauthid>.html',
        views.bindsuccess,  # 显示绑定成功信息的视图函数
        name='bindsuccess'  # URL名称，用于反向解析
    ),
    
    # OAuth登录入口点
    # 用户点击第三方登录按钮时访问的URL
    path(
        r'oauth/oauthlogin',
        views.oauthlogin,  # 处理OAuth登录初始化的视图函数
        name='oauthlogin'  # URL名称，用于反向解析
    )
]
