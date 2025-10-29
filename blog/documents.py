import time

import elasticsearch.client
from django.conf import settings
from elasticsearch_dsl import Document, InnerDoc, Date, Integer, Long, Text, Object, GeoPoint, Keyword, Boolean
from elasticsearch_dsl.connections import connections

from blog.models import Article

# 检查是否启用了Elasticsearch
ELASTICSEARCH_ENABLED = hasattr(settings, 'ELASTICSEARCH_DSL')

if ELASTICSEARCH_ENABLED:
    # 创建Elasticsearch连接
    connections.create_connection(
        hosts=[settings.ELASTICSEARCH_DSL['default']['hosts']])
    from elasticsearch import Elasticsearch

    # 初始化Elasticsearch客户端
    es = Elasticsearch(settings.ELASTICSEARCH_DSL['default']['hosts'])
    from elasticsearch.client import IngestClient

    # 创建Ingest客户端用于处理pipeline
    c = IngestClient(es)
    try:
        # 检查是否已存在geoip pipeline
        c.get_pipeline('geoip')
    except elasticsearch.exceptions.NotFoundError:
        # 如果不存在，创建geoip pipeline用于IP地址的地理位置解析
        c.put_pipeline('geoip', body='''{
              "description" : "Add geoip info",
              "processors" : [
                {
                  "geoip" : {
                    "field" : "ip"
                  }
                }
              ]
            }''')


# GeoIP地理位置信息内嵌文档类
class GeoIp(InnerDoc):
    continent_name = Keyword()  # 大洲名称
    country_iso_code = Keyword()  # 国家ISO代码
    country_name = Keyword()  # 国家名称
    location = GeoPoint()  # 地理位置坐标


# 用户代理浏览器信息内嵌文档类
class UserAgentBrowser(InnerDoc):
    Family = Keyword()  # 浏览器家族
    Version = Keyword()  # 浏览器版本


# 用户代理操作系统信息内嵌文档类
class UserAgentOS(UserAgentBrowser):
    pass  # 继承自UserAgentBrowser，具有相同的字段结构


# 用户代理设备信息内嵌文档类
class UserAgentDevice(InnerDoc):
    Family = Keyword()  # 设备家族
    Brand = Keyword()  # 设备品牌
    Model = Keyword()  # 设备型号


# 完整的用户代理信息内嵌文档类
class UserAgent(InnerDoc):
    browser = Object(UserAgentBrowser, required=False)  # 浏览器信息对象
    os = Object(UserAgentOS, required=False)  # 操作系统信息对象
    device = Object(UserAgentDevice, required=False)  # 设备信息对象
    string = Text()  # 原始用户代理字符串
    is_bot = Boolean()  # 是否为爬虫


# 性能监控文档类 - 记录请求耗时等信息
class ElapsedTimeDocument(Document):
    url = Keyword()  # 请求的URL
    time_taken = Long()  # 请求耗时（毫秒）
    log_datetime = Date()  # 日志记录时间
    ip = Keyword()  # 客户端IP地址
    geoip = Object(GeoIp, required=False)  # 地理位置信息
    useragent = Object(UserAgent, required=False)  # 用户代理信息

    class Index:
        name = 'performance'  # Elasticsearch索引名称
        settings = {
            "number_of_shards": 1,  # 分片数量
            "number_of_replicas": 0  # 副本数量
        }

    class Meta:
        doc_type = 'ElapsedTime'  # 文档类型


# 性能监控文档管理器类
class ElaspedTimeDocumentManager:
    @staticmethod
    def build_index():
        # 构建性能监控索引
        from elasticsearch import Elasticsearch
        client = Elasticsearch(settings.ELASTICSEARCH_DSL['default']['hosts'])
        res = client.indices.exists(index="performance")
        if not res:
            ElapsedTimeDocument.init()  # 如果索引不存在则创建

    @staticmethod
    def delete_index():
        # 删除性能监控索引
        from elasticsearch import Elasticsearch
        es = Elasticsearch(settings.ELASTICSEARCH_DSL['default']['hosts'])
        es.indices.delete(index='performance', ignore=[400, 404])

    @staticmethod
    def create(url, time_taken, log_datetime, useragent, ip):
        # 创建新的性能监控文档
        ElaspedTimeDocumentManager.build_index()
        
        # 构建用户代理信息
        ua = UserAgent()
        ua.browser = UserAgentBrowser()
        ua.browser.Family = useragent.browser.family
        ua.browser.Version = useragent.browser.version_string

        ua.os = UserAgentOS()
        ua.os.Family = useragent.os.family
        ua.os.Version = useragent.os.version_string

        ua.device = UserAgentDevice()
        ua.device.Family = useragent.device.family
        ua.device.Brand = useragent.device.brand
        ua.device.Model = useragent.device.model
        ua.string = useragent.ua_string
        ua.is_bot = useragent.is_bot

        # 创建文档并使用geoip pipeline处理IP地址
        doc = ElapsedTimeDocument(
            meta={
                'id': int(
                    round(
                        time.time() *
                        1000))  # 使用当前时间戳作为文档ID
            },
            url=url,
            time_taken=time_taken,
            log_datetime=log_datetime,
            useragent=ua, ip=ip)
        doc.save(pipeline="geoip")  # 保存文档并应用geoip pipeline


# 文章搜索文档类
class ArticleDocument(Document):
    body = Text(analyzer='ik_max_word', search_analyzer='ik_smart')  # 使用IK中文分词器
    title = Text(analyzer='ik_max_word', search_analyzer='ik_smart')
    author = Object(properties={
        'nickname': Text(analyzer='ik_max_word', search_analyzer='ik_smart'),
        'id': Integer()
    })  # 作者对象
    category = Object(properties={
        'name': Text(analyzer='ik_max_word', search_analyzer='ik_smart'),
        'id': Integer()
    })  # 分类对象
    tags = Object(properties={
        'name': Text(analyzer='ik_max_word', search_analyzer='ik_smart'),
        'id': Integer()
    })  # 标签对象（数组）

    pub_time = Date()  # 发布时间
    status = Text()  # 状态
    comment_status = Text()  # 评论状态
    type = Text()  # 类型
    views = Integer()  # 浏览量
    article_order = Integer()  # 文章排序

    class Index:
        name = 'blog'  # 文章索引名称
        settings = {
            "number_of_shards": 1,  # 分片数量
            "number_of_replicas": 0  # 副本数量
        }

    class Meta:
        doc_type = 'Article'  # 文档类型


# 文章文档管理器类
class ArticleDocumentManager():

    def __init__(self):
        self.create_index()

    def create_index(self):
        # 创建文章索引
        ArticleDocument.init()

    def delete_index(self):
        # 删除文章索引
        from elasticsearch import Elasticsearch
        es = Elasticsearch(settings.ELASTICSEARCH_DSL['default']['hosts'])
        es.indices.delete(index='blog', ignore=[400, 404])

    def convert_to_doc(self, articles):
        # 将Django文章模型转换为Elasticsearch文档
        return [
            ArticleDocument(
                meta={
                    'id': article.id},  # 使用文章ID作为文档ID
                body=article.body,
                title=article.title,
                author={
                    'nickname': article.author.username,
                    'id': article.author.id},
                category={
                    'name': article.category.name,
                    'id': article.category.id},
                tags=[
                    {
                        'name': t.name,
                        'id': t.id} for t in article.tags.all()],  # 处理多对多标签关系
                pub_time=article.pub_time,
                status=article.status,
                comment_status=article.comment_status,
                type=article.type,
                views=article.views,
                article_order=article.article_order) for article in articles]

    def rebuild(self, articles=None):
        # 重建文章索引
        ArticleDocument.init()
        articles = articles if articles else Article.objects.all()
        docs = self.convert_to_doc(articles)
        for doc in docs:
            doc.save()  # 保存所有文档到Elasticsearch

    def update_docs(self, docs):
        # 更新文档
        for doc in docs:
            doc.save()
