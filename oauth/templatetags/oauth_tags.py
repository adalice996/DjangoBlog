from django import template
from django.urls import reverse

from oauth.oauthmanager import get_oauth_apps

# 创建Django模板库实例，用于注册自定义模板标签
register = template.Library()


# 注册一个包含标签(inclusion tag)，用于渲染OAuth第三方登录应用列表
# 这个标签会渲染'oauth/oauth_applications.html'模板
@register.inclusion_tag('oauth/oauth_applications.html')
def load_oauth_applications(request):
    """
    自定义模板标签：加载并生成OAuth第三方登录应用列表
    
    功能：
    - 获取所有配置的OAuth应用
    - 为每个OAuth应用生成登录URL
    - 将应用数据传递给模板进行渲染
    
    参数：
    request: HttpRequest对象，用于获取当前请求路径
    
    返回：
    字典，包含'apps'键，对应的值是OAuth应用列表
    """
    
    # 从oauth管理器获取所有可用的OAuth应用配置
    applications = get_oauth_apps()
    
    # 检查是否有可用的OAuth应用
    if applications:
        # 生成OAuth登录视图的URL，'oauth:oauthlogin'是URL配置中的名称
        baseurl = reverse('oauth:oauthlogin')
        # 获取当前请求的完整路径，用于登录成功后重定向回原页面
        path = request.get_full_path()

        # 使用map函数遍历所有OAuth应用，为每个应用生成登录URL
        # 生成格式：(应用类型, 登录URL)
        apps = list(map(lambda x: (
            x.ICON_NAME,  # OAuth应用的图标名称/类型标识（如'github', 'weibo'等）
            # 格式化登录URL，包含参数：
            # - type: OAuth应用类型
            # - next_url: 登录成功后跳转的URL
            '{baseurl}?type={type}&next_url={next}'.format(
                baseurl=baseurl, 
                type=x.ICON_NAME, 
                next=path
            )), 
            applications  # 要遍历的OAuth应用列表
        ))
    else:
        # 如果没有可用的OAuth应用，返回空列表
        apps = []
    
    # 返回模板上下文，包含OAuth应用数据
    return {
        'apps': apps  # 应用列表，每个元素是元组(应用类型, 登录URL)
    }
