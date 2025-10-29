import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.paginator import Paginator
from django.templatetags.static import static
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import BlogUser
from blog.forms import BlogSearchForm
from blog.models import Article, Category, Tag, SideBar, Links
from blog.templatetags.blog_tags import load_pagination_info, load_articletags
from djangoblog.utils import get_current_site, get_sha256
from oauth.models import OAuthUser, OAuthConfig


# 创建测试类
class ArticleTest(TestCase):
    def setUp(self):
        # 在每个测试方法执行前运行，初始化测试环境
        self.client = Client()  # 创建测试客户端
        self.factory = RequestFactory()  # 创建请求工厂

    def test_validate_article(self):
        # 测试文章验证和相关的功能
        site = get_current_site().domain  # 获取当前站点域名
        # 获取或创建测试用户
        user = BlogUser.objects.get_or_create(
            email="liangliangyy@gmail.com",
            username="liangliangyy")[0]
        user.set_password("liangliangyy")  # 设置密码
        user.is_staff = True  # 设置为管理员
        user.is_superuser = True  # 设置为超级用户
        user.save()  # 保存用户
        
        # 测试用户详情页
        response = self.client.get(user.get_absolute_url())
        self.assertEqual(response.status_code, 200)  # 断言响应状态码为200
        
        # 测试管理后台页面
        response = self.client.get('/admin/servermanager/emailsendlog/')
        response = self.client.get('admin/admin/logentry/')
        
        # 创建侧边栏
        s = SideBar()
        s.sequence = 1  # 排序
        s.name = 'test'  # 名称
        s.content = 'test content'  # 内容
        s.is_enable = True  # 启用
        s.save()  # 保存

        # 创建分类
        category = Category()
        category.name = "category"  # 分类名称
        category.creation_time = timezone.now()  # 创建时间
        category.last_mod_time = timezone.now()  # 修改时间
        category.save()  # 保存

        # 创建标签
        tag = Tag()
        tag.name = "nicetag"  # 标签名称
        tag.save()  # 保存

        # 创建文章
        article = Article()
        article.title = "nicetitle"  # 文章标题
        article.body = "nicecontent"  # 文章内容
        article.author = user  # 作者
        article.category = category  # 分类
        article.type = 'a'  # 类型：文章
        article.status = 'p'  # 状态：已发布

        article.save()  # 保存文章
        self.assertEqual(0, article.tags.count())  # 断言初始标签数量为0
        article.tags.add(tag)  # 添加标签
        article.save()  # 保存文章
        self.assertEqual(1, article.tags.count())  # 断言标签数量为1

        # 批量创建20篇文章用于测试分页等
        for i in range(20):
            article = Article()
            article.title = "nicetitle" + str(i)
            article.body = "nicetitle" + str(i)
            article.author = user
            article.category = category
            article.type = 'a'
            article.status = 'p'
            article.save()
            article.tags.add(tag)
            article.save()
            
        # 如果启用了Elasticsearch，构建搜索索引并测试搜索
        from blog.documents import ELASTICSEARCH_ENABLED
        if ELASTICSEARCH_ENABLED:
            call_command("build_index")  # 构建搜索索引
            response = self.client.get('/search', {'q': 'nicetitle'})  # 搜索测试
            self.assertEqual(response.status_code, 200)  # 断言搜索成功

        # 测试文章详情页
        response = self.client.get(article.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        
        # 测试蜘蛛通知功能
        from djangoblog.spider_notify import SpiderNotify
        SpiderNotify.notify(article.get_absolute_url())
        
        # 测试标签页
        response = self.client.get(tag.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        # 测试分类页
        response = self.client.get(category.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        # 测试搜索功能
        response = self.client.get('/search', {'q': 'django'})
        self.assertEqual(response.status_code, 200)
        
        # 测试文章标签模板标签
        s = load_articletags(article)
        self.assertIsNotNone(s)

        # 用户登录
        self.client.login(username='liangliangyy', password='liangliangyy')

        # 测试文章归档页
        response = self.client.get(reverse('blog:archives'))
        self.assertEqual(response.status_code, 200)

        # 测试分页功能 - 所有文章
        p = Paginator(Article.objects.all(), settings.PAGINATE_BY)
        self.check_pagination(p, '', '')

        # 测试分页功能 - 按标签归档
        p = Paginator(Article.objects.filter(tags=tag), settings.PAGINATE_BY)
        self.check_pagination(p, '分类标签归档', tag.slug)

        # 测试分页功能 - 按作者归档
        p = Paginator(
            Article.objects.filter(
                author__username='liangliangyy'), settings.PAGINATE_BY)
        self.check_pagination(p, '作者文章归档', 'liangliangyy')

        # 测试分页功能 - 按分类归档
        p = Paginator(Article.objects.filter(category=category), settings.PAGINATE_BY)
        self.check_pagination(p, '分类目录归档', category.slug)

        # 测试搜索表单
        f = BlogSearchForm()
        f.search()
        
        # 测试百度蜘蛛通知
        from djangoblog.spider_notify import SpiderNotify
        SpiderNotify.baidu_notify([article.get_full_url()])

        # 测试Gravatar头像功能
        from blog.templatetags.blog_tags import gravatar_url, gravatar
        u = gravatar_url('liangliangyy@gmail.com')
        u = gravatar('liangliangyy@gmail.com')

        # 创建友情链接并测试链接页
        link = Links(
            sequence=1,
            name="lylinux",
            link='https://wwww.lylinux.net')
        link.save()
        response = self.client.get('/links.html')
        self.assertEqual(response.status_code, 200)

        # 测试RSS订阅
        response = self.client.get('/feed/')
        self.assertEqual(response.status_code, 200)

        # 测试网站地图
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)

        # 测试管理后台操作
        self.client.get("/admin/blog/article/1/delete/")
        self.client.get('/admin/servermanager/emailsendlog/')
        self.client.get('/admin/admin/logentry/')
        self.client.get('/admin/admin/logentry/1/change/')

    def check_pagination(self, p, type, value):
        # 检查分页功能
        for page in range(1, p.num_pages + 1):
            s = load_pagination_info(p.page(page), type, value)
            self.assertIsNotNone(s)
            # 测试上一页链接
            if s['previous_url']:
                response = self.client.get(s['previous_url'])
                self.assertEqual(response.status_code, 200)
            # 测试下一页链接
            if s['next_url']:
                response = self.client.get(s['next_url'])
                self.assertEqual(response.status_code, 200)

    def test_image(self):
        # 测试图片上传功能
        import requests
        # 下载测试图片
        rsp = requests.get(
            'https://www.python.org/static/img/python-logo.png')
        imagepath = os.path.join(settings.BASE_DIR, 'python.png')
        with open(imagepath, 'wb') as file:
            file.write(rsp.content)
            
        # 测试未授权上传
        rsp = self.client.post('/upload')
        self.assertEqual(rsp.status_code, 403)  # 断言返回403禁止访问
        
        # 生成签名
        sign = get_sha256(get_sha256(settings.SECRET_KEY))
        with open(imagepath, 'rb') as file:
            # 创建上传文件
            imgfile = SimpleUploadedFile(
                'python.png', file.read(), content_type='image/jpg')
            form_data = {'python.png': imgfile}
            # 测试带签名的上传
            rsp = self.client.post(
                '/upload?sign=' + sign, form_data, follow=True)
            self.assertEqual(rsp.status_code, 200)  # 断言上传成功
        os.remove(imagepath)  # 删除临时文件
        
        # 测试头像保存和邮件发送功能
        from djangoblog.utils import save_user_avatar, send_email
        send_email(['qq@qq.com'], 'testTitle', 'testContent')  # 发送测试邮件
        save_user_avatar(  # 保存用户头像
            'https://www.python.org/static/img/python-logo.png')

    def test_errorpage(self):
        # 测试错误页面
        rsp = self.client.get('/eee')  # 访问不存在的页面
        self.assertEqual(rsp.status_code, 404)  # 断言返回404错误

    def test_commands(self):
        # 测试管理命令
        # 创建测试用户
        user = BlogUser.objects.get_or_create(
            email="liangliangyy@gmail.com",
            username="liangliangyy")[0]
        user.set_password("liangliangyy")
        user.is_staff = True
        user.is_superuser = True
        user.save()

        # 创建OAuth配置
        c = OAuthConfig()
        c.type = 'qq'  # QQ登录
        c.appkey = 'appkey'  # 应用密钥
        c.appsecret = 'appsecret'  # 应用秘钥
        c.save()

        # 创建OAuth用户
        u = OAuthUser()
        u.type = 'qq'
        u.openid = 'openid'
        u.user = user
        u.picture = static("/blog/img/avatar.png")  # 头像
        u.metadata = '''
{
"figureurl": "https://qzapp.qlogo.cn/qzapp/101513904/C740E30B4113EAA80E0D9918ABC78E82/30"
}'''  # 元数据
        u.save()

        # 创建另一个OAuth用户
        u = OAuthUser()
        u.type = 'qq'
        u.openid = 'openid1'
        u.picture = 'https://qzapp.qlogo.cn/qzapp/101513904/C740E30B4113EAA80E0D9918ABC78E82/30'
        u.metadata = '''
        {
       "figureurl": "https://qzapp.qlogo.cn/qzapp/101513904/C740E30B4113EAA80E0D9918ABC78E82/30"
        }'''
        u.save()

        # 执行各种管理命令
        from blog.documents import ELASTICSEARCH_ENABLED
        if ELASTICSEARCH_ENABLED:
            call_command("build_index")  # 构建搜索索引
        call_command("ping_baidu", "all")  # 百度推送
        call_command("create_testdata")  # 创建测试数据
        call_command("clear_cache")  # 清除缓存
        call_command("sync_user_avatar")  # 同步用户头像
        call_command("build_search_words")  # 构建搜索词
