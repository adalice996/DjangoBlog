# 导入类型提示模块
import typing
# 导入时间间隔类
from datetime import timedelta

# 导入Django缓存系统
from django.core.cache import cache
# 导入国际化翻译函数
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

# 导入自定义邮件发送工具
from djangoblog.utils import send_email

# 定义验证码的生存时间（Time To Live），5分钟有效
_code_ttl = timedelta(minutes=5)


def send_verify_email(to_mail: str, code: str, subject: str = _("Verify Email")):
    """
    发送验证邮件
    用于发送包含验证码的邮件到指定邮箱
    
    Args:
        to_mail (str): 接收邮件的邮箱地址
        code (str): 验证码内容
        subject (str): 邮件主题，默认为"Verify Email"（支持国际化）
    """
    # 构建邮件HTML内容，包含验证码信息
    html_content = _(
        "You are resetting the password, the verification code is：%(code)s, valid within 5 minutes, please keep it "
        "properly") % {'code': code}
    
    # 调用邮件发送函数发送邮件
    send_email([to_mail], subject, html_content)


def verify(email: str, code: str) -> typing.Optional[str]:
    """
    验证验证码是否正确
    比较用户输入的验证码与缓存中存储的验证码是否一致
    
    Args:
        email (str): 用户邮箱地址，作为缓存的key
        code (str): 用户输入的验证码
        
    Returns:
        typing.Optional[str]: 
            - None: 验证通过
            - str: 错误信息（验证失败时返回的错误描述）
            
    Note:
        这里的错误处理不太合理，应该采用raise抛出异常
        否则调用方也需要对error进行处理，增加了调用复杂度
    """
    # 从缓存中获取该邮箱对应的验证码
    cache_code = get_code(email)
    
    # 比较用户输入的验证码与缓存中的验证码
    if cache_code != code:
        # 验证码不匹配，返回错误信息
        return gettext("Verification code error")
    
    # 验证通过，返回None
    # 注意：这里没有显式返回None，Python函数默认返回None


def set_code(email: str, code: str):
    """
    将验证码存储到缓存中
    使用邮箱作为key，验证码作为value，设置5分钟过期时间
    
    Args:
        email (str): 邮箱地址，作为缓存的key
        code (str): 验证码，作为缓存的value
    """
    # 将验证码存入缓存，设置过期时间为5分钟
    cache.set(email, code, _code_ttl.seconds)


def get_code(email: str) -> typing.Optional[str]:
    """
    从缓存中获取验证码
    
    Args:
        email (str): 邮箱地址，作为缓存的key
        
    Returns:
        typing.Optional[str]: 
            - str: 找到的验证码
            - None: 验证码不存在或已过期
    """
    # 从缓存中获取指定邮箱的验证码
    return cache.get(email)
