# 导入获取用户模型的方法
from django.contrib.auth import get_user_model
# 导入Django默认的模型认证后端基类
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameModelBackend(ModelBackend):
    """
    自定义认证后端
    允许用户使用用户名或邮箱登录系统
    
    继承自ModelBackend，扩展了Django的默认认证方式
    提供更灵活的用户登录体验
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        用户认证方法
        根据用户名或邮箱验证用户身份
        
        Args:
            request: HTTP请求对象
            username: 用户输入的用户名或邮箱
            password: 用户输入的密码
            **kwargs: 其他关键字参数
            
        Returns:
            User: 认证成功的用户对象
            None: 认证失败
        """
        # 判断输入的是邮箱还是用户名
        if '@' in username:
            # 如果包含@符号，认为是邮箱登录
            kwargs = {'email': username}
        else:
            # 否则认为是用户名登录
            kwargs = {'username': username}
            
        try:
            # 根据用户名或邮箱查找用户
            user = get_user_model().objects.get(**kwargs)
            
            # 验证密码是否正确
            if user.check_password(password):
                # 密码验证成功，返回用户对象
                return user
            else:
                # 密码错误，返回None（不暴露具体错误信息）
                return None
                
        except get_user_model().DoesNotExist:
            # 用户不存在，返回None
            return None

    def get_user(self, user_id):
        """
        根据用户ID获取用户对象
        用于会话认证中从用户ID恢复用户对象
        
        Args:
            user_id: 用户的主键ID
            
        Returns:
            User: 用户对象
            None: 用户不存在
        """
        try:
            # 根据主键ID查找用户
            return get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            # 用户不存在，返回None
            return None
