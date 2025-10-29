import logging

from django.utils import timezone

from djangoblog.utils import cache, get_blog_setting
from .models import Category, Article

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)


# SEO上下文处理器
# 这个函数用于向所有模板传递SEO相关的变量和全局设置
def seo_processor(requests):
    # 缓存键名
    key = 'seo_processor'
    
    # 尝试从缓存中获取数据
    value = cache.get(key)
    if value:
        # 如果缓存存在，直接返回缓存数据
        return value
    else:
        # 缓存不存在，记录日志并重新生成数据
        logger.info('set processor cache.')
        
        # 获取博客全局设置
        setting = get_blog_setting()
        
        # 构建包含所有SEO和全局设置的数据字典
        value = {
            # 基本站点信息
            'SITE_NAME': setting.site_name,
            'SITE_SEO_DESCRIPTION': setting.site_seo_description,
            'SITE_DESCRIPTION': setting.site_description,
            'SITE_KEYWORDS': setting.site_keywords,
            'SITE_BASE_URL': requests.scheme + '://' + requests.get_host() + '/',
            
            # Google AdSense 广告相关设置
            'SHOW_GOOGLE_ADSENSE': setting.show_google_adsense,
            'GOOGLE_ADSENSE_CODES': setting.google_adsense_codes,
            
            # 文章相关设置
            'ARTICLE_SUB_LENGTH': setting.article_sub_length,
            
            # 导航数据
            'nav_category_list': Category.objects.all(),  # 所有分类用于导航
            'nav_pages': Article.objects.filter(
                type='p',  # 页面类型
                status='p'),  # 已发布状态
            
            # 评论系统设置
            'OPEN_SITE_COMMENT': setting.open_site_comment,
            'COMMENT_NEED_REVIEW': setting.comment_need_review,
            
            # 备案和统计代码
            'BEIAN_CODE': setting.beian_code,
            'ANALYTICS_CODE': setting.analytics_code,
            "BEIAN_CODE_GONGAN": setting.gongan_beiancode,
            "SHOW_GONGAN_CODE": setting.show_gongan_code,
            
            # 动态数据
            "CURRENT_YEAR": timezone.now().year,  # 当前年份
            
            # 全局页头和页脚
            "GLOBAL_HEADER": setting.global_header,
            "GLOBAL_FOOTER": setting.global_footer,
        }
        
        # 将数据存入缓存，有效期10小时
        cache.set(key, value, 60 * 60 * 10)
        
        # 返回数据字典
        return value
