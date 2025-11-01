import json
import logging
import os
import urllib.parse
from abc import ABCMeta, abstractmethod

import requests

from djangoblog.utils import cache_decorator
from oauth.models import OAuthUser, OAuthConfig

# 获取日志记录器
logger = logging.getLogger(__name__)


class OAuthAccessTokenException(Exception):
    '''
    OAuth授权失败异常类
    当获取access token失败时抛出此异常
    '''
    pass


class BaseOauthManager(metaclass=ABCMeta):
    """
    OAuth管理器基类（抽象类）
    定义所有OAuth服务商通用的接口和方法
    """
    
    # 抽象属性，子类必须实现
    AUTH_URL = None  # 授权页面URL
    TOKEN_URL = None  # 获取token的URL
    API_URL = None  # 获取用户信息的API URL
    ICON_NAME = None  # 服务商图标名称

    def __init__(self, access_token=None, openid=None):
        """
        初始化OAuth管理器
        
        Args:
            access_token: 访问令牌
            openid: 用户在第三方平台的唯一标识
        """
        self.access_token = access_token
        self.openid = openid

    @property
    def is_access_token_set(self):
        """检查access token是否已设置"""
        return self.access_token is not None

    @property
    def is_authorized(self):
        """检查是否已完成授权（有token和openid）"""
        return self.is_access_token_set and self.access_token is not None and self.openid is not None

    @abstractmethod
    def get_authorization_url(self, nexturl='/'):
        """获取授权URL（抽象方法）"""
        pass

    @abstractmethod
    def get_access_token_by_code(self, code):
        """通过授权码获取access token（抽象方法）"""
        pass

    @abstractmethod
    def get_oauth_userinfo(self):
        """获取用户信息（抽象方法）"""
        pass

    @abstractmethod
    def get_picture(self, metadata):
        """从元数据中提取用户头像（抽象方法）"""
        pass

    def do_get(self, url, params, headers=None):
        """执行GET请求"""
        rsp = requests.get(url=url, params=params, headers=headers)
        logger.info(rsp.text)
        return rsp.text

    def do_post(self, url, params, headers=None):
        """执行POST请求"""
        rsp = requests.post(url, params, headers=headers)
        logger.info(rsp.text)
        return rsp.text

    def get_config(self):
        """从数据库获取OAuth配置"""
        value = OAuthConfig.objects.filter(type=self.ICON_NAME)
        return value[0] if value else None


class WBOauthManager(BaseOauthManager):
    """
    微博OAuth管理器
    实现微博平台的OAuth2.0认证流程
    """
    AUTH_URL = 'https://api.weibo.com/oauth2/authorize'
    TOKEN_URL = 'https://api.weibo.com/oauth2/access_token'
    API_URL = 'https://api.weibo.com/2/users/show.json'
    ICON_NAME = 'weibo'

    def __init__(self, access_token=None, openid=None):
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        super(WBOauthManager, self).__init__(access_token=access_token, openid=openid)

    def get_authorization_url(self, nexturl='/'):
        """生成微博授权URL"""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.callback_url + '&next_url=' + nexturl
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        """使用授权码获取access token"""
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.callback_url
        }
        rsp = self.do_post(self.TOKEN_URL, params)

        obj = json.loads(rsp)
        if 'access_token' in obj:
            self.access_token = str(obj['access_token'])
            self.openid = str(obj['uid'])
            return self.get_oauth_userinfo()
        else:
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        """获取微博用户信息"""
        if not self.is_authorized:
            return None
        params = {
            'uid': self.openid,
            'access_token': self.access_token
        }
        rsp = self.do_get(self.API_URL, params)
        try:
            datas = json.loads(rsp)
            user = OAuthUser()
            user.metadata = rsp
            user.picture = datas['avatar_large']  # 用户头像
            user.nickname = datas['screen_name']  # 用户昵称
            user.openid = datas['id']  # 用户ID
            user.type = 'weibo'  # 平台类型
            user.token = self.access_token  # 访问令牌
            if 'email' in datas and datas['email']:
                user.email = datas['email']  # 用户邮箱
            return user
        except Exception as e:
            logger.error(e)
            logger.error('weibo oauth error.rsp:' + rsp)
            return None

    def get_picture(self, metadata):
        """从元数据中提取微博用户头像"""
        datas = json.loads(metadata)
        return datas['avatar_large']


class ProxyManagerMixin:
    """
    代理管理器混入类
    为需要代理的OAuth管理器提供代理支持
    """
    def __init__(self, *args, **kwargs):
        # 从环境变量获取代理设置
        if os.environ.get("HTTP_PROXY"):
            self.proxies = {
                "http": os.environ.get("HTTP_PROXY"),
                "https": os.environ.get("HTTP_PROXY")
            }
        else:
            self.proxies = None

    def do_get(self, url, params, headers=None):
        """使用代理执行GET请求"""
        rsp = requests.get(url=url, params=params, headers=headers, proxies=self.proxies)
        logger.info(rsp.text)
        return rsp.text

    def do_post(self, url, params, headers=None):
        """使用代理执行POST请求"""
        rsp = requests.post(url, params, headers=headers, proxies=self.proxies)
        logger.info(rsp.text)
        return rsp.text


class GoogleOauthManager(ProxyManagerMixin, BaseOauthManager):
    """
    谷歌OAuth管理器
    实现Google平台的OAuth2.0认证流程
    """
    AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://www.googleapis.com/oauth2/v4/token'
    API_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'
    ICON_NAME = 'google'

    def __init__(self, access_token=None, openid=None):
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        super(GoogleOauthManager, self).__init__(access_token=access_token, openid=openid)

    def get_authorization_url(self, nexturl='/'):
        """生成谷歌授权URL"""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.callback_url,
            'scope': 'openid email',  # 请求的权限范围
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        """使用授权码获取access token"""
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.callback_url
        }
        rsp = self.do_post(self.TOKEN_URL, params)

        obj = json.loads(rsp)
        if 'access_token' in obj:
            self.access_token = str(obj['access_token'])
            self.openid = str(obj['id_token'])
            logger.info(self.ICON_NAME + ' oauth ' + rsp)
            return self.access_token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        """获取谷歌用户信息"""
        if not self.is_authorized:
            return None
        params = {
            'access_token': self.access_token
        }
        rsp = self.do_get(self.API_URL, params)
        try:
            datas = json.loads(rsp)
            user = OAuthUser()
            user.metadata = rsp
            user.picture = datas['picture']  # 用户头像
            user.nickname = datas['name']  # 用户昵称
            user.openid = datas['sub']  # 用户ID
            user.token = self.access_token  # 访问令牌
            user.type = 'google'  # 平台类型
            if datas['email']:
                user.email = datas['email']  # 用户邮箱
            return user
        except Exception as e:
            logger.error(e)
            logger.error('google oauth error.rsp:' + rsp)
            return None

    def get_picture(self, metadata):
        """从元数据中提取谷歌用户头像"""
        datas = json.loads(metadata)
        return datas['picture']


class GitHubOauthManager(ProxyManagerMixin, BaseOauthManager):
    """
    GitHub OAuth管理器
    实现GitHub平台的OAuth2.0认证流程
    """
    AUTH_URL = 'https://github.com/login/oauth/authorize'
    TOKEN_URL = 'https://github.com/login/oauth/access_token'
    API_URL = 'https://api.github.com/user'
    ICON_NAME = 'github'

    def __init__(self, access_token=None, openid=None):
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        super(GitHubOauthManager, self).__init__(access_token=access_token, openid=openid)

    def get_authorization_url(self, next_url='/'):
        """生成GitHub授权URL"""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': f'{self.callback_url}&next_url={next_url}',
            'scope': 'user'  # 请求用户信息权限
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        """使用授权码获取access token"""
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.callback_url
        }
        rsp = self.do_post(self.TOKEN_URL, params)

        from urllib import parse
        r = parse.parse_qs(rsp)
        if 'access_token' in r:
            self.access_token = (r['access_token'][0])
            return self.access_token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        """获取GitHub用户信息"""
        rsp = self.do_get(self.API_URL, params={}, headers={
            "Authorization": "token " + self.access_token  # GitHub需要使用token认证
        })
        try:
            datas = json.loads(rsp)
            user = OAuthUser()
            user.picture = datas['avatar_url']  # 用户头像
            user.nickname = datas['name']  # 用户昵称
            user.openid = datas['id']  # 用户ID
            user.type = 'github'  # 平台类型
            user.token = self.access_token  # 访问令牌
            user.metadata = rsp  # 原始元数据
            if 'email' in datas and datas['email']:
                user.email = datas['email']  # 用户邮箱
            return user
        except Exception as e:
            logger.error(e)
            logger.error('github oauth error.rsp:' + rsp)
            return None

    def get_picture(self, metadata):
        """从元数据中提取GitHub用户头像"""
        datas = json.loads(metadata)
        return datas['avatar_url']


class FaceBookOauthManager(ProxyManagerMixin, BaseOauthManager):
    """
    Facebook OAuth管理器
    实现Facebook平台的OAuth2.0认证流程
    """
    AUTH_URL = 'https://www.facebook.com/v16.0/dialog/oauth'
    TOKEN_URL = 'https://graph.facebook.com/v16.0/oauth/access_token'
    API_URL = 'https://graph.facebook.com/me'
    ICON_NAME = 'facebook'

    def __init__(self, access_token=None, openid=None):
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        super(FaceBookOauthManager, self).__init__(access_token=access_token, openid=openid)

    def get_authorization_url(self, next_url='/'):
        """生成Facebook授权URL"""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.callback_url,
            'scope': 'email,public_profile'  # 请求邮箱和公开资料权限
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        """使用授权码获取access token"""
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.callback_url
        }
        rsp = self.do_post(self.TOKEN_URL, params)

        obj = json.loads(rsp)
        if 'access_token' in obj:
            token = str(obj['access_token'])
            self.access_token = token
            return self.access_token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        """获取Facebook用户信息"""
        params = {
            'access_token': self.access_token,
            'fields': 'id,name,picture,email'  # 指定需要的字段
        }
        try:
            rsp = self.do_get(self.API_URL, params)
            datas = json.loads(rsp)
            user = OAuthUser()
            user.nickname = datas['name']  # 用户昵称
            user.openid = datas['id']  # 用户ID
            user.type = 'facebook'  # 平台类型
            user.token = self.access_token  # 访问令牌
            user.metadata = rsp  # 原始元数据
            if 'email' in datas and datas['email']:
                user.email = datas['email']  # 用户邮箱
            if 'picture' in datas and datas['picture'] and datas['picture']['data'] and datas['picture']['data']['url']:
                user.picture = str(datas['picture']['data']['url'])  # 用户头像
            return user
        except Exception as e:
            logger.error(e)
            return None

    def get_picture(self, metadata):
        """从元数据中提取Facebook用户头像"""
        datas = json.loads(metadata)
        return str(datas['picture']['data']['url'])


class QQOauthManager(BaseOauthManager):
    """
    QQ OAuth管理器
    实现QQ平台的OAuth2.0认证流程
    """
    AUTH_URL = 'https://graph.qq.com/oauth2.0/authorize'
    TOKEN_URL = 'https://graph.qq.com/oauth2.0/token'
    API_URL = 'https://graph.qq.com/user/get_user_info'
    OPEN_ID_URL = 'https://graph.qq.com/oauth2.0/me'  # QQ需要单独获取openid
    ICON_NAME = 'qq'

    def __init__(self, access_token=None, openid=None):
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        super(QQOauthManager, self).__init__(access_token=access_token, openid=openid)

    def get_authorization_url(self, next_url='/'):
        """生成QQ授权URL"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.callback_url + '&next_url=' + next_url,
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        """使用授权码获取access token"""
        params = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.callback_url
        }
        rsp = self.do_get(self.TOKEN_URL, params)
        if rsp:
            d = urllib.parse.parse_qs(rsp)
            if 'access_token' in d:
                token = d['access_token']
                self.access_token = token[0]
                return token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_open_id(self):
        """获取QQ用户的openid（QQ需要单独调用接口获取openid）"""
        if self.is_access_token_set:
            params = {
                'access_token': self.access_token
            }
            rsp = self.do_get(self.OPEN_ID_URL, params)
            if rsp:
                # 处理JSONP响应
                rsp = rsp.replace('callback(', '').replace(')', '').replace(';', '')
                obj = json.loads(rsp)
                openid = str(obj['openid'])
                self.openid = openid
                return openid

    def get_oauth_userinfo(self):
        """获取QQ用户信息"""
        openid = self.get_open_id()
        if openid:
            params = {
                'access_token': self.access_token,
                'oauth_consumer_key': self.client_id,
                'openid': self.openid
            }
            rsp = self.do_get(self.API_URL, params)
            logger.info(rsp)
            obj = json.loads(rsp)
            user = OAuthUser()
            user.nickname = obj['nickname']  # 用户昵称
            user.openid = openid  # 用户ID
            user.type = 'qq'  # 平台类型
            user.token = self.access_token  # 访问令牌
            user.metadata = rsp  # 原始元数据
            if 'email' in obj:
                user.email = obj['email']  # 用户邮箱
            if 'figureurl' in obj:
                user.picture = str(obj['figureurl'])  # 用户头像
            return user

    def get_picture(self, metadata):
        """从元数据中提取QQ用户头像"""
        datas = json.loads(metadata)
        return str(datas['figureurl'])


@cache_decorator(expiration=100 * 60)
def get_oauth_apps():
    """
    获取所有启用的OAuth应用
    使用缓存装饰器，缓存100分钟
    """
    configs = OAuthConfig.objects.filter(is_enable=True).all()
    if not configs:
        return []
    configtypes = [x.type for x in configs]
    applications = BaseOauthManager.__subclasses__()
    apps = [x() for x in applications if x().ICON_NAME.lower() in configtypes]
    return apps


def get_manager_by_type(type):
    """
    根据类型获取对应的OAuth管理器
    
    Args:
        type: OAuth服务商类型（weibo、google、github等）
    
    Returns:
        对应的OAuth管理器实例，如果未找到返回None
    """
    applications = get_oauth_apps()
    if applications:
        finds = list(filter(lambda x: x.ICON_NAME.lower() == type.lower(), applications))
        if finds:
            return finds[0]
    return None