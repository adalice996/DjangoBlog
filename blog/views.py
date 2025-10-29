import logging
import os
import uuid

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from haystack.views import SearchView

from blog.models import Article, Category, LinkShowType, Links, Tag
from comments.forms import CommentForm
from djangoblog.plugin_manage import hooks
from djangoblog.plugin_manage.hook_constants import ARTICLE_CONTENT_HOOK_NAME
from djangoblog.utils import cache, get_blog_setting, get_sha256

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)


# 文章列表视图基类
class ArticleListView(ListView):
    # template_name属性用于指定使用哪个模板进行渲染
    template_name = 'blog/article_index.html'

    # context_object_name属性用于给上下文变量取名（在模板中使用该名字）
    context_object_name = 'article_list'

    # 页面类型，分类目录或标签列表等
    page_type = ''
    paginate_by = settings.PAGINATE_BY  # 分页大小，从设置中获取
    page_kwarg = 'page'  # URL中页码参数的名称
    link_type = LinkShowType.L  # 链接显示类型

    def get_view_cache_key(self):
        # 获取视图缓存键
        return self.request.get['pages']

    @property
    def page_number(self):
        # 获取当前页码的属性
        page_kwarg = self.page_kwarg
        page = self.kwargs.get(
            page_kwarg) or self.request.GET.get(page_kwarg) or 1
        return page

    def get_queryset_cache_key(self):
        """
        子类重写.获得queryset的缓存key
        """
        raise NotImplementedError()

    def get_queryset_data(self):
        """
        子类重写.获取queryset的数据
        """
        raise NotImplementedError()

    def get_queryset_from_cache(self, cache_key):
        '''
        缓存页面数据
        :param cache_key: 缓存key
        :return: 缓存的数据或新查询的数据
        '''
        value = cache.get(cache_key)
        if value:
            logger.info('get view cache.key:{key}'.format(key=cache_key))
            return value
        else:
            article_list = self.get_queryset_data()
            cache.set(cache_key, article_list)
            logger.info('set view cache.key:{key}'.format(key=cache_key))
            return article_list

    def get_queryset(self):
        '''
        重写默认，从缓存获取数据
        :return: 文章列表数据
        '''
        key = self.get_queryset_cache_key()
        value = self.get_queryset_from_cache(key)
        return value

    def get_context_data(self, **kwargs):
        # 添加上下文数据
        kwargs['linktype'] = self.link_type
        return super(ArticleListView, self).get_context_data(**kwargs)


# 首页视图
class IndexView(ArticleListView):
    '''
    首页视图，显示所有已发布的文章
    '''
    # 友情链接类型
    link_type = LinkShowType.I

    def get_queryset_data(self):
        # 获取首页文章列表数据
        article_list = Article.objects.filter(type='a', status='p')
        return article_list

    def get_queryset_cache_key(self):
        # 生成首页缓存键
        cache_key = 'index_{page}'.format(page=self.page_number)
        return cache_key


# 文章详情视图
class ArticleDetailView(DetailView):
    '''
    文章详情页面视图
    '''
    template_name = 'blog/article_detail.html'  # 模板文件
    model = Article  # 关联的模型
    pk_url_kwarg = 'article_id'  # URL中主键参数的名称
    context_object_name = "article"  # 上下文变量名称

    def get_context_data(self, **kwargs):
        # 获取文章详情页的上下文数据
        comment_form = CommentForm()  # 评论表单

        # 获取文章评论列表
        article_comments = self.object.comment_list()
        parent_comments = article_comments.filter(parent_comment=None)
        blog_setting = get_blog_setting()
        
        # 评论分页
        paginator = Paginator(parent_comments, blog_setting.article_comment_count)
        page = self.request.GET.get('comment_page', '1')
        if not page.isnumeric():
            page = 1
        else:
            page = int(page)
            if page < 1:
                page = 1
            if page > paginator.num_pages:
                page = paginator.num_pages

        p_comments = paginator.page(page)  # 当前页的评论
        next_page = p_comments.next_page_number() if p_comments.has_next() else None
        prev_page = p_comments.previous_page_number() if p_comments.has_previous() else None

        # 生成评论分页URL
        if next_page:
            kwargs[
                'comment_next_page_url'] = self.object.get_absolute_url() + f'?comment_page={next_page}#commentlist-container'
        if prev_page:
            kwargs[
                'comment_prev_page_url'] = self.object.get_absolute_url() + f'?comment_page={prev_page}#commentlist-container'
        
        # 添加上下文数据
        kwargs['form'] = comment_form
        kwargs['article_comments'] = article_comments
        kwargs['p_comments'] = p_comments
        kwargs['comment_count'] = len(
            article_comments) if article_comments else 0

        kwargs['next_article'] = self.object.next_article  # 下一篇文章
        kwargs['prev_article'] = self.object.prev_article  # 上一篇文章

        context = super(ArticleDetailView, self).get_context_data(**kwargs)
        article = self.object
        # Action Hook, 通知插件"文章详情已获取"
        hooks.run_action('after_article_body_get', article=article, request=self.request)
        return context


# 分类详情视图
class CategoryDetailView(ArticleListView):
    '''
    分类目录列表视图
    '''
    page_type = "分类目录归档"

    def get_queryset_data(self):
        # 获取分类下的文章列表
        slug = self.kwargs['category_name']
        category = get_object_or_404(Category, slug=slug)

        categoryname = category.name
        self.categoryname = categoryname
        # 获取所有子分类的名称
        categorynames = list(
            map(lambda c: c.name, category.get_sub_categorys()))
        # 查询这些分类下的文章
        article_list = Article.objects.filter(
            category__name__in=categorynames, status='p')
        return article_list

    def get_queryset_cache_key(self):
        # 生成分类页面缓存键
        slug = self.kwargs['category_name']
        category = get_object_or_404(Category, slug=slug)
        categoryname = category.name
        self.categoryname = categoryname
        cache_key = 'category_list_{categoryname}_{page}'.format(
            categoryname=categoryname, page=self.page_number)
        return cache_key

    def get_context_data(self, **kwargs):
        # 添加上下文数据
        categoryname = self.categoryname
        try:
            categoryname = categoryname.split('/')[-1]  # 获取分类名的最后部分
        except BaseException:
            pass
        kwargs['page_type'] = CategoryDetailView.page_type
        kwargs['tag_name'] = categoryname
        return super(CategoryDetailView, self).get_context_data(**kwargs)


# 作者详情视图
class AuthorDetailView(ArticleListView):
    '''
    作者详情页视图
    '''
    page_type = '作者文章归档'

    def get_queryset_cache_key(self):
        # 生成作者页面缓存键
        from uuslug import slugify
        author_name = slugify(self.kwargs['author_name'])
        cache_key = 'author_{author_name}_{page}'.format(
            author_name=author_name, page=self.page_number)
        return cache_key

    def get_queryset_data(self):
        # 获取作者的文章列表
        author_name = self.kwargs['author_name']
        article_list = Article.objects.filter(
            author__username=author_name, type='a', status='p')
        return article_list

    def get_context_data(self, **kwargs):
        # 添加上下文数据
        author_name = self.kwargs['author_name']
        kwargs['page_type'] = AuthorDetailView.page_type
        kwargs['tag_name'] = author_name
        return super(AuthorDetailView, self).get_context_data(**kwargs)


# 标签详情视图
class TagDetailView(ArticleListView):
    '''
    标签列表页面视图
    '''
    page_type = '分类标签归档'

    def get_queryset_data(self):
        # 获取标签下的文章列表
        slug = self.kwargs['tag_name']
        tag = get_object_or_404(Tag, slug=slug)
        tag_name = tag.name
        self.name = tag_name
        article_list = Article.objects.filter(
            tags__name=tag_name, type='a', status='p')
        return article_list

    def get_queryset_cache_key(self):
        # 生成标签页面缓存键
        slug = self.kwargs['tag_name']
        tag = get_object_or_404(Tag, slug=slug)
        tag_name = tag.name
        self.name = tag_name
        cache_key = 'tag_{tag_name}_{page}'.format(
            tag_name=tag_name, page=self.page_number)
        return cache_key

    def get_context_data(self, **kwargs):
        # 添加上下文数据
        tag_name = self.name
        kwargs['page_type'] = TagDetailView.page_type
        kwargs['tag_name'] = tag_name
        return super(TagDetailView, self).get_context_data(**kwargs)


# 文章归档视图
class ArchivesView(ArticleListView):
    '''
    文章归档页面视图，显示所有文章的时间线
    '''
    page_type = '文章归档'
    paginate_by = None  # 归档页面不使用分页
    page_kwarg = None  # 没有页码参数
    template_name = 'blog/article_archives.html'  # 使用专门的归档模板

    def get_queryset_data(self):
        # 获取所有已发布的文章
        return Article.objects.filter(status='p').all()

    def get_queryset_cache_key(self):
        # 生成归档页面缓存键
        cache_key = 'archives'
        return cache_key


# 友情链接列表视图
class LinkListView(ListView):
    '''
    友情链接页面视图
    '''
    model = Links  # 关联的模型
    template_name = 'blog/links_list.html'  # 模板文件

    def get_queryset(self):
        # 只获取启用的友情链接
        return Links.objects.filter(is_enable=True)


# Elasticsearch搜索视图
class EsSearchView(SearchView):
    '''
    自定义搜索视图，基于Haystack
    '''
    def get_context(self):
        # 获取搜索结果的上下文数据
        paginator, page = self.build_page()
        context = {
            "query": self.query,  # 搜索关键词
            "form": self.form,  # 搜索表单
            "page": page,  # 当前页
            "paginator": paginator,  # 分页器
            "suggestion": None,  # 搜索建议
        }
        # 如果有拼写建议，添加到上下文
        if hasattr(self.results, "query") and self.results.query.backend.include_spelling:
            context["suggestion"] = self.results.query.get_spelling_suggestion()
        context.update(self.extra_context())

        return context


# 文件上传视图
@csrf_exempt  # 免除CSRF验证
def fileupload(request):
    """
    文件上传视图，提供图床功能
    该方法需自己写调用端来上传图片，该方法仅提供图床功能
    :param request: HTTP请求
    :return: 上传文件的URL或错误响应
    """
    if request.method == 'POST':
        # 验证签名
        sign = request.GET.get('sign', None)
        if not sign:
            return HttpResponseForbidden()
        if not sign == get_sha256(get_sha256(settings.SECRET_KEY)):
            return HttpResponseForbidden()
        
        response = []
        # 处理所有上传的文件
        for filename in request.FILES:
            timestr = timezone.now().strftime('%Y/%m/%d')  # 按日期组织目录
            imgextensions = ['jpg', 'png', 'jpeg', 'bmp']  # 图片扩展名
            fname = u''.join(str(filename))
            isimage = len([i for i in imgextensions if fname.find(i) >= 0]) > 0
            
            # 创建保存目录
            base_dir = os.path.join(settings.STATICFILES, "files" if not isimage else "image", timestr)
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
                
            # 生成保存路径
            savepath = os.path.normpath(os.path.join(base_dir, f"{uuid.uuid4().hex}{os.path.splitext(filename)[-1]}"))
            if not savepath.startswith(base_dir):
                return HttpResponse("only for post")
                
            # 保存文件
            with open(savepath, 'wb+') as wfile:
                for chunk in request.FILES[filename].chunks():
                    wfile.write(chunk)
                    
            # 如果是图片，进行压缩优化
            if isimage:
                from PIL import Image
                image = Image.open(savepath)
                image.save(savepath, quality=20, optimize=True)
                
            url = static(savepath)  # 生成静态文件URL
            response.append(url)
        return HttpResponse(response)

    else:
        return HttpResponse("only for post")


# 404错误页面视图
def page_not_found_view(
        request,
        exception,
        template_name='blog/error_page.html'):
    """
    404页面未找到错误处理视图
    """
    if exception:
        logger.error(exception)
    url = request.get_full_path()
    return render(request,
                  template_name,
                  {'message': _('Sorry, the page you requested is not found, please click the home page to see other?'),
                   'statuscode': '404'},
                  status=404)


# 500服务器错误视图
def server_error_view(request, template_name='blog/error_page.html'):
    """
    500服务器错误处理视图
    """
    return render(request,
                  template_name,
                  {'message': _('Sorry, the server is busy, please click the home page to see other?'),
                   'statuscode': '500'},
                  status=500)


# 403权限拒绝视图
def permission_denied_view(
        request,
        exception,
        template_name='blog/error_page.html'):
    """
    403权限拒绝错误处理视图
    """
    if exception:
        logger.error(exception)
    return render(
        request, template_name, {
            'message': _('Sorry, you do not have permission to access this page?'),
            'statuscode': '403'}, status=403)


# 清理缓存视图
def clean_cache_view(request):
    """
    清理所有缓存视图
    """
    cache.clear()
    return HttpResponse('ok')
