from django.urls import path
from django.views.decorators.cache import cache_page

from . import views

# 定义应用命名空间，用于URL反向解析
app_name = "blog"

# URL模式配置，定义博客应用的URL路由
urlpatterns = [
    # 首页 - 显示文章列表
    path(
        r'',  # 根路径
        views.IndexView.as_view(),  # 使用类视图处理首页
        name='index'),  # URL名称，用于反向解析
    
    # 首页分页 - 显示指定页码的文章列表
    path(
        r'page/<int:page>/',  # 带页码参数的路径
        views.IndexView.as_view(),  # 使用相同的类视图，但会处理分页
        name='index_page'),  # URL名称
    
    # 文章详情页 - 通过年月日和文章ID访问具体文章
    path(
        r'article/<int:year>/<int:month>/<int:day>/<int:article_id>.html',  # 包含年月日和文章ID的URL
        views.ArticleDetailView.as_view(),  # 文章详情类视图
        name='detailbyid'),  # URL名称
    
    # 分类详情页 - 显示指定分类下的文章列表
    path(
        r'category/<slug:category_name>.html',  # 分类名称作为slug参数
        views.CategoryDetailView.as_view(),  # 分类详情类视图
        name='category_detail'),  # URL名称
    
    # 分类详情分页页 - 显示指定分类下指定页码的文章列表
    path(
        r'category/<slug:category_name>/<int:page>.html',  # 分类名称和页码参数
        views.CategoryDetailView.as_view(),  # 使用相同的分类详情视图
        name='category_detail_page'),  # URL名称
    
    # 作者详情页 - 显示指定作者的文章列表
    path(
        r'author/<author_name>.html',  # 作者名称参数
        views.AuthorDetailView.as_view(),  # 作者详情类视图
        name='author_detail'),  # URL名称
    
    # 作者详情分页页 - 显示指定作者下指定页码的文章列表
    path(
        r'author/<author_name>/<int:page>.html',  # 作者名称和页码参数
        views.AuthorDetailView.as_view(),  # 使用相同的作者详情视图
        name='author_detail_page'),  # URL名称
    
    # 标签详情页 - 显示指定标签下的文章列表
    path(
        r'tag/<slug:tag_name>.html',  # 标签名称作为slug参数
        views.TagDetailView.as_view(),  # 标签详情类视图
        name='tag_detail'),  # URL名称
    
    # 标签详情分页页 - 显示指定标签下指定页码的文章列表
    path(
        r'tag/<slug:tag_name>/<int:page>.html',  # 标签名称和页码参数
        views.TagDetailView.as_view(),  # 使用相同的标签详情视图
        name='tag_detail_page'),  # URL名称
    
    # 文章归档页 - 显示所有文章的按时间归档，使用缓存加速
    path(
        'archives.html',  # 归档页面路径
        cache_page(  # 使用缓存装饰器，缓存1小时（60*60秒）
            60 * 60)(
            views.ArchivesView.as_view()),  # 归档视图类
        name='archives'),  # URL名称
    
    # 友情链接页 - 显示所有友情链接
    path(
        'links.html',  # 友情链接页面路径
        views.LinkListView.as_view(),  # 链接列表类视图
        name='links'),  # URL名称
    
    # 文件上传接口 - 处理文件上传请求
    path(
        r'upload',  # 上传路径
        views.fileupload,  # 文件上传函数视图
        name='upload'),  # URL名称
    
    # 缓存清理接口 - 清理应用缓存
    path(
        r'clean',  # 清理缓存路径
        views.clean_cache_view,  # 清理缓存函数视图
        name='clean'),  # URL名称
]
