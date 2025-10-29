import logging

from django import forms
from haystack.forms import SearchForm

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)


# 自定义博客搜索表单类，继承自Haystack的SearchForm
class BlogSearchForm(SearchForm):
    # 定义查询字段，设置为必填字段
    querydata = forms.CharField(required=True)

    def search(self):
        # 调用父类的search方法获取搜索结果
        datas = super(BlogSearchForm, self).search()
        
        # 如果表单验证不通过，返回空搜索结果
        if not self.is_valid():
            return self.no_query_found()

        # 如果查询数据存在，记录查询日志
        if self.cleaned_data['querydata']:
            logger.info(self.cleaned_data['querydata'])
            
        # 返回搜索结果
        return datas
