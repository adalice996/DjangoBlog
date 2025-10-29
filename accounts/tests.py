# 导入Django测试相关模块
from django.test import Client, RequestFactory, TestCase
# 导入URL反向解析
from django.urls import reverse
# 导入时间相关工具
from django.utils import timezone
# 导入国际化翻译
from django.utils.translation import gettext_lazy as _

# 导入自定义用户模型
from accounts.models import BlogUser
# 导入博客文章和分类模型
from blog.models import Article, Category
# 导入工具函数
from djangoblog.utils import *
# 导入当前应用的工具模块
from . import utils


# 测试类注释
# Create your tests here.

class AccountTest(TestCase):
    """
    账户功能测试类
    测试用户注册、登录、密码重置等核心功能
    """
    
    def setUp(self):
        """
        测试初始化方法
        在每个测试方法执行前运行，准备测试数据
        """
        # 创建测试客户端，用于模拟HTTP请求
        self.client = Client()
        # 创建请求工厂，用于构建请求对象
        self.factory = RequestFactory()
        # 创建测试用户
        self.blog_user = BlogUser.objects.create_user(
            username="test",
            email="admin@admin.com",
            password="12345678"
        )
        # 设置测试用的新密码
        self.new_test = "xxx123--="

    def test_validate_account(self):
        """
        测试账户验证功能
        包括超级用户创建、登录、文章管理等功能
        """
        # 获取当前站点域名
        site = get_current_site().domain
        
        # 创建超级用户
        user = BlogUser.objects.create_superuser(
            email="liangliangyy1@gmail.com",
            username="liangliangyy1",
            password="qwer!@#$ggg")
        
        # 验证用户创建成功
        testuser = BlogUser.objects.get(username='liangliangyy1')

        # 测试登录功能
        loginresult = self.client.login(
            username='liangliangyy1',
            password='qwer!@#$ggg')
        self.assertEqual(loginresult, True)  # 断言登录成功
        
        # 测试访问管理后台
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)  # 断言能够正常访问

        # 创建测试分类
        category = Category()
        category.name = "categoryaaa"
        category.creation_time = timezone.now()
        category.last_modify_time = timezone.now()
        category.save()

        # 创建测试文章
        article = Article()
        article.title = "nicetitleaaa"
        article.body = "nicecontentaaa"
        article.author = user
        article.category = category
        article.type = 'a'  # 文章类型
        article.status = 'p'  # 发布状态
        article.save()

        # 测试访问文章管理页面
        response = self.client.get(article.get_admin_url())
        self.assertEqual(response.status_code, 200)  # 断言能够正常访问

    def test_validate_register(self):
        """
        测试用户注册流程
        包括注册、邮箱验证、登录、权限管理等
        """
        # 验证注册前邮箱不存在
        self.assertEquals(
            0, len(
                BlogUser.objects.filter(
                    email='user123@user.com')))
        
        # 发送注册请求
        response = self.client.post(reverse('account:register'), {
            'username': 'user1233',
            'email': 'user123@user.com',
            'password1': 'password123!q@wE#R$T',
            'password2': 'password123!q@wE#R$T',
        })
        
        # 验证注册后用户创建成功
        self.assertEquals(
            1, len(
                BlogUser.objects.filter(
                    email='user123@user.com')))
        
        # 获取新创建的用户
        user = BlogUser.objects.filter(email='user123@user.com')[0]
        
        # 生成邮箱验证签名
        sign = get_sha256(get_sha256(settings.SECRET_KEY + str(user.id)))
        path = reverse('accounts:result')
        url = '{path}?type=validation&id={id}&sign={sign}'.format(
            path=path, id=user.id, sign=sign)
        
        # 测试邮箱验证页面
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # 测试用户登录
        self.client.login(username='user1233', password='password123!q@wE#R$T')
        
        # 提升用户权限为超级用户
        user = BlogUser.objects.filter(email='user123@user.com')[0]
        user.is_superuser = True
        user.is_staff = True
        user.save()
        
        # 清除侧边栏缓存
        delete_sidebar_cache()
        
        # 创建测试分类和文章
        category = Category()
        category.name = "categoryaaa"
        category.creation_time = timezone.now()
        category.last_modify_time = timezone.now()
        category.save()

        article = Article()
        article.category = category
        article.title = "nicetitle333"
        article.body = "nicecontentttt"
        article.author = user
        article.type = 'a'
        article.status = 'p'
        article.save()

        # 测试登录状态下访问文章管理页面
        response = self.client.get(article.get_admin_url())
        self.assertEqual(response.status_code, 200)

        # 测试退出登录
        response = self.client.get(reverse('account:logout'))
        self.assertIn(response.status_code, [301, 302, 200])  # 重定向响应

        # 测试退出后访问管理页面会被重定向
        response = self.client.get(article.get_admin_url())
        self.assertIn(response.status_code, [301, 302, 200])

        # 测试重新登录（使用错误密码）
        response = self.client.post(reverse('account:login'), {
            'username': 'user1233',
            'password': 'password123'  # 错误的密码
        })
        self.assertIn(response.status_code, [301, 302, 200])

        # 测试错误密码登录后访问管理页面会被重定向
        response = self.client.get(article.get_admin_url())
        self.assertIn(response.status_code, [301, 302, 200])

    def test_verify_email_code(self):
        """
        测试邮箱验证码功能
        包括验证码生成、发送、验证等
        """
        to_email = "admin@admin.com"
        code = generate_code()  # 生成验证码
        
        # 保存验证码到缓存或数据库
        utils.set_code(to_email, code)
        # 发送验证邮件
        utils.send_verify_email(to_email, code)

        # 测试正确的邮箱和验证码
        err = utils.verify("admin@admin.com", code)
        self.assertEqual(err, None)  # 断言验证通过，无错误

        # 测试错误的邮箱
        err = utils.verify("admin@123.com", code)
        self.assertEqual(type(err), str)  # 断言返回错误信息

    def test_forget_password_email_code_success(self):
        """
        测试成功发送忘记密码验证码
        """
        resp = self.client.post(
            path=reverse("account:forget_password_code"),
            data=dict(email="admin@admin.com")
        )

        self.assertEqual(resp.status_code, 200)  # 断言请求成功
        self.assertEqual(resp.content.decode("utf-8"), "ok")  # 断言返回成功消息

    def test_forget_password_email_code_fail(self):
        """
        测试发送忘记密码验证码的失败情况
        """
        # 测试空邮箱
        resp = self.client.post(
            path=reverse("account:forget_password_code"),
            data=dict()
        )
        self.assertEqual(resp.content.decode("utf-8"), "错误的邮箱")

        # 测试无效邮箱格式
        resp = self.client.post(
            path=reverse("account:forget_password_code"),
            data=dict(email="admin@com")
        )
        self.assertEqual(resp.content.decode("utf-8"), "错误的邮箱")

    def test_forget_password_email_success(self):
        """
        测试成功重置密码
        """
        code = generate_code()
        # 设置验证码
        utils.set_code(self.blog_user.email, code)
        
        # 构造重置密码请求数据
        data = dict(
            new_password1=self.new_test,
            new_password2=self.new_test,
            email=self.blog_user.email,
            code=code,
        )
        
        # 发送重置密码请求
        resp = self.client.post(
            path=reverse("account:forget_password"),
            data=data
        )
        self.assertEqual(resp.status_code, 302)  # 断言重定向响应

        # 验证用户密码是否修改成功
        blog_user = BlogUser.objects.filter(
            email=self.blog_user.email,
        ).first()  # type: BlogUser
        self.assertNotEqual(blog_user, None)  # 断言用户存在
        self.assertEqual(blog_user.check_password(data["new_password1"]), True)  # 断言密码修改成功

    def test_forget_password_email_not_user(self):
        """
        测试使用不存在的邮箱重置密码
        """
        data = dict(
            new_password1=self.new_test,
            new_password2=self.new_test,
            email="123@123.com",  # 不存在的邮箱
            code="123456",
        )
        resp = self.client.post(
            path=reverse("account:forget_password"),
            data=data
        )

        self.assertEqual(resp.status_code, 200)  # 断言返回错误页面而非重定向

    def test_forget_password_email_code_error(self):
        """
        测试使用错误验证码重置密码
        """
        code = generate_code()
        utils.set_code(self.blog_user.email, code)
        data = dict(
            new_password1=self.new_test,
            new_password2=self.new_test,
            email=self.blog_user.email,
            code="111111",  # 错误的验证码
        )
        resp = self.client.post(
            path=reverse("account:forget_password"),
            data=data
        )

        self.assertEqual(resp.status_code, 200)  # 断言验证失败，停留在当前页面
