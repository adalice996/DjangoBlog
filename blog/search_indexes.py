from haystack import indexes

from blog.models import Article


# 文章搜索索引类
# 这个类定义了Haystack搜索引擎如何索引Article模型的数据
class ArticleIndex(indexes.SearchIndex, indexes.Indexable):
    # 定义主搜索字段，document=True表示这是主要的搜索内容字段
    # use_template=True表示使用模板文件来构建这个字段的内容
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        """
        返回这个索引对应的Django模型类
        :return: Article模型类
        """
        return Article

    def index_queryset(self, using=None):
        """
        返回需要被索引的查询集
        这里只索引状态为已发布（'p'）的文章
        :param using: 可选参数，指定使用的搜索引擎后端
        :return: 已发布文章的查询集
        """
        return self.get_model().objects.filter(status='p')
