import json
from unittest.mock import patch

from django.conf import settings
from django.contrib import auth
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from djangoblog.utils import get_sha256
from oauth.models import OAuthConfig
from oauth.oauthmanager import BaseOauthManager


# Create your tests here.
class OAuthConfigTest(TestCase):
    """
    OAuth配置模型测试类
    测试OAuth配置相关的功能
    """
    def setUp(self):
        """测试初始化设置"""
        self.client = Client()  # Django测试客户端
        self.factory = RequestFactory()  # 请求工厂，用于创建请求对象

    def test_oauth_login_test(self):
        """测试OAuth登录流程"""
        # 创建微博OAuth配置
        c = OAuthConfig()
        c.type = 'weibo'
        c.appkey = 'appkey'
        c.appsecret = 'appsecret'
        c.save()

        # 测试OAuth登录请求，应该重定向到微博授权页面
        response = self.client.get('/oauth/oauthlogin?type=weibo')
        self.assertEqual(response.status_code, 302)  # 验证重定向状态码
        self.assertTrue("api.weibo.com" in response.url)  # 验证重定向到微博

        # 测试授权回调，应该重定向到首页
        response = self.client.get('/oauth/authorize?type=weibo&code=code')
        self.assertEqual(response.status_code, 302)  # 验证重定向状态码
        self.assertEqual(response.url, '/')  # 验证重定向到首页


class OauthLoginTest(TestCase):
    """
    OAuth登录流程测试类
    测试各种OAuth服务商的登录功能
    """
    def setUp(self) -> None:
        """测试初始化设置"""
        self.client = Client()
        self.factory = RequestFactory()
        self.apps = self.init_apps()  # 初始化所有OAuth应用配置

    def init_apps(self):
        """初始化所有OAuth应用配置"""
        # 获取所有OAuth管理器的子类并实例化
        applications = [p() for p in BaseOauthManager.__subclasses__()]
        for application in applications:
            # 为每个OAuth类型创建配置
            c = OAuthConfig()
            c.type = application.ICON_NAME.lower()
            c.appkey = 'appkey'
            c.appsecret = 'appsecret'
            c.save()
        return applications

    def get_app_by_type(self, type):
        """根据类型获取对应的OAuth应用"""
        for app in self.apps:
            if app.ICON_NAME.lower() == type:
                return app

    @patch("oauth.oauthmanager.WBOauthManager.do_post")
    @patch("oauth.oauthmanager.WBOauthManager.do_get")
    def test_weibo_login(self, mock_do_get, mock_do_post):
        """测试微博OAuth登录流程"""
        weibo_app = self.get_app_by_type('weibo')
        assert weibo_app  # 验证微博应用存在
        
        # 获取授权URL
        url = weibo_app.get_authorization_url()
        
        # 模拟API响应
        mock_do_post.return_value = json.dumps({
            "access_token": "access_token",
            "uid": "uid"
        })
        mock_do_get.return_value = json.dumps({
            "avatar_large": "avatar_large",
            "screen_name": "screen_name",
            "id": "id",
            "email": "email",
        })
        
        # 测试获取用户信息
        userinfo = weibo_app.get_access_token_by_code('code')
        self.assertEqual(userinfo.token, 'access_token')  # 验证token
        self.assertEqual(userinfo.openid, 'id')  # 验证用户ID

    @patch("oauth.oauthmanager.GoogleOauthManager.do_post")
    @patch("oauth.oauthmanager.GoogleOauthManager.do_get")
    def test_google_login(self, mock_do_get, mock_do_post):
        """测试谷歌OAuth登录流程"""
        google_app = self.get_app_by_type('google')
        assert google_app
        
        url = google_app.get_authorization_url()
        
        # 模拟API响应
        mock_do_post.return_value = json.dumps({
            "access_token": "access_token",
            "id_token": "id_token",
        })
        mock_do_get.return_value = json.dumps({
            "picture": "picture",
            "name": "name",
            "sub": "sub",
            "email": "email",
        })
        
        # 测试获取token和用户信息
        token = google_app.get_access_token_by_code('code')
        userinfo = google_app.get_oauth_userinfo()
        self.assertEqual(userinfo.token, 'access_token')
        self.assertEqual(userinfo.openid, 'sub')  # 谷歌使用sub作为用户ID

    @patch("oauth.oauthmanager.GitHubOauthManager.do_post")
    @patch("oauth.oauthmanager.GitHubOauthManager.do_get")
    def test_github_login(self, mock_do_get, mock_do_post):
        """测试GitHub OAuth登录流程"""
        github_app = self.get_app_by_type('github')
        assert github_app
        
        url = github_app.get_authorization_url()
        self.assertTrue("github.com" in url)  # 验证GitHub域名
        self.assertTrue("client_id" in url)  # 验证包含client_id参数
        
        # 模拟GitHub特有的响应格式
        mock_do_post.return_value = "access_token=gho_16C7e42F292c6912E7710c838347Ae178B4a&scope=repo%2Cgist&token_type=bearer"
        mock_do_get.return_value = json.dumps({
            "avatar_url": "avatar_url",
            "name": "name",
            "id": "id",
            "email": "email",
        })
        
        token = github_app.get_access_token_by_code('code')
        userinfo = github_app.get_oauth_userinfo()
        self.assertEqual(userinfo.token, 'gho_16C7e42F292c6912E7710c838347Ae178B4a')
        self.assertEqual(userinfo.openid, 'id')

    @patch("oauth.oauthmanager.FaceBookOauthManager.do_post")
    @patch("oauth.oauthmanager.FaceBookOauthManager.do_get")
    def test_facebook_login(self, mock_do_get, mock_do_post):
        """测试Facebook OAuth登录流程"""
        facebook_app = self.get_app_by_type('facebook')
        assert facebook_app
        
        url = facebook_app.get_authorization_url()
        self.assertTrue("facebook.com" in url)  # 验证Facebook域名
        
        # 模拟API响应
        mock_do_post.return_value = json.dumps({
            "access_token": "access_token",
        })
        mock_do_get.return_value = json.dumps({
            "name": "name",
            "id": "id",
            "email": "email",
            "picture": {
                "data": {
                    "url": "url"
                }
            }
        })
        
        token = facebook_app.get_access_token_by_code('code')
        userinfo = facebook_app.get_oauth_userinfo()
        self.assertEqual(userinfo.token, 'access_token')

    @patch("oauth.oauthmanager.QQOauthManager.do_get", side_effect=[
        # 模拟QQ OAuth的三次API调用响应
        'access_token=access_token&expires_in=3600',  # 获取token响应
        'callback({"client_id":"appid","openid":"openid"} );',  # 获取openid响应(JSONP格式)
        json.dumps({  # 获取用户信息响应
            "nickname": "nickname",
            "email": "email",
            "figureurl": "figureurl",
            "openid": "openid",
        })
    ])
    def test_qq_login(self, mock_do_get):
        """测试QQ OAuth登录流程"""
        qq_app = self.get_app_by_type('qq')
        assert qq_app
        
        url = qq_app.get_authorization_url()
        self.assertTrue("qq.com" in url)  # 验证QQ域名
        
        # 测试QQ登录流程（QQ需要三次API调用）
        token = qq_app.get_access_token_by_code('code')
        userinfo = qq_app.get_oauth_userinfo()
        self.assertEqual(userinfo.token, 'access_token')

    @patch("oauth.oauthmanager.WBOauthManager.do_post")
    @patch("oauth.oauthmanager.WBOauthManager.do_get")
    def test_weibo_authoriz_login_with_email(self, mock_do_get, mock_do_post):
        """测试微博登录（有邮箱的情况）- 完整集成测试"""
        
        # 模拟API响应
        mock_do_post.return_value = json.dumps({
            "access_token": "access_token",
            "uid": "uid"
        })
        mock_user_info = {
            "avatar_large": "avatar_large",
            "screen_name": "screen_name1",
            "id": "id",
            "email": "email",
        }
        mock_do_get.return_value = json.dumps(mock_user_info)

        # 测试登录重定向
        response = self.client.get('/oauth/oauthlogin?type=weibo')
        self.assertEqual(response.status_code, 302)
        self.assertTrue("api.weibo.com" in response.url)

        # 测试授权回调
        response = self.client.get('/oauth/authorize?type=weibo&code=code')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')  # 有邮箱直接登录成功，跳转首页

        # 验证用户已登录
        user = auth.get_user(self.client)
        assert user.is_authenticated
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, mock_user_info['screen_name'])
        self.assertEqual(user.email, mock_user_info['email'])
        
        # 清理登录状态
        self.client.logout()

        # 测试重复登录
        response = self.client.get('/oauth/authorize?type=weibo&code=code')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

        user = auth.get_user(self.client)
        assert user.is_authenticated
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, mock_user_info['screen_name'])
        self.assertEqual(user.email, mock_user_info['email'])

    @patch("oauth.oauthmanager.WBOauthManager.do_post")
    @patch("oauth.oauthmanager.WBOauthManager.do_get")
    def test_weibo_authoriz_login_without_email(self, mock_do_get, mock_do_post):
        """测试微博登录（无邮箱的情况）- 完整集成测试"""
        
        # 模拟API响应（无邮箱）
        mock_do_post.return_value = json.dumps({
            "access_token": "access_token",
            "uid": "uid"
        })
        mock_user_info = {
            "avatar_large": "avatar_large",
            "screen_name": "screen_name1",
            "id": "id",
            # 注意：没有email字段
        }
        mock_do_get.return_value = json.dumps(mock_user_info)

        # 测试登录重定向
        response = self.client.get('/oauth/oauthlogin?type=weibo')
        self.assertEqual(response.status_code, 302)
        self.assertTrue("api.weibo.com" in response.url)

        # 测试授权回调 - 无邮箱时应该重定向到邮箱补充页面
        response = self.client.get('/oauth/authorize?type=weibo&code=code')
        self.assertEqual(response.status_code, 302)

        # 解析OAuth用户ID
        oauth_user_id = int(response.url.split('/')[-1].split('.')[0])
        self.assertEqual(response.url, f'/oauth/requireemail/{oauth_user_id}.html')

        # 提交邮箱表单
        response = self.client.post(response.url, {
            'email': 'test@gmail.com', 
            'oauthid': oauth_user_id
        })

        self.assertEqual(response.status_code, 302)
        
        # 生成邮箱确认签名
        sign = get_sha256(settings.SECRET_KEY +
                          str(oauth_user_id) + settings.SECRET_KEY)

        # 验证绑定成功URL
        url = reverse('oauth:bindsuccess', kwargs={
            'oauthid': oauth_user_id,
        })
        self.assertEqual(response.url, f'{url}?type=email')

        # 模拟邮箱确认链接点击
        path = reverse('oauth:email_confirm', kwargs={
            'id': oauth_user_id,
            'sign': sign
        })
        response = self.client.get(path)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/oauth/bindsuccess/{oauth_user_id}.html?type=success')
        
        # 验证最终用户状态
        user = auth.get_user(self.client)
        from oauth.models import OAuthUser
        oauth_user = OAuthUser.objects.get(author=user)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, mock_user_info['screen_name'])
        self.assertEqual(user.email, 'test@gmail.com')
        self.assertEqual(oauth_user.pk, oauth_user_id)  # 验证OAuth用户关联
