import logging
import time

from ipware import get_client_ip
from user_agents import parse

# 导入Elasticsearch相关模块
from blog.documents import ELASTICSEARCH_ENABLED, ElaspedTimeDocumentManager

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)


# 在线用户中间件类 - 用于记录页面渲染时间和用户访问信息
class OnlineMiddleware(object):
    def __init__(self, get_response=None):
        # 初始化中间件，get_response是Django处理链中的下一个中间件或视图
        self.get_response = get_response
        super().__init__()

    def __call__(self, request):
        ''' 页面渲染时间监控 '''
        # 记录请求开始时间
        start_time = time.time()
        
        # 调用下一个中间件或视图处理请求，获取响应
        response = self.get_response(request)
        
        # 获取用户代理字符串和客户端IP地址
        http_user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip, _ = get_client_ip(request)
        
        # 解析用户代理信息
        user_agent = parse(http_user_agent)
        
        # 检查响应是否为流式响应（如文件下载），非流式响应才进行处理
        if not response.streaming:
            try:
                # 计算页面渲染耗时
                cast_time = time.time() - start_time
                
                # 如果启用了Elasticsearch，记录性能数据
                if ELASTICSEARCH_ENABLED:
                    # 将耗时转换为毫秒并保留两位小数
                    time_taken = round((cast_time) * 1000, 2)
                    url = request.path  # 获取请求路径
                    from django.utils import timezone
                    
                    # 创建性能监控文档
                    ElaspedTimeDocumentManager.create(
                        url=url,
                        time_taken=time_taken,
                        log_datetime=timezone.now(),  # 使用Django时区感知的时间
                        useragent=user_agent,
                        ip=ip)
                
                # 在响应内容中替换占位符为实际渲染时间
                # 注意：这要求模板中有 <!!LOAD_TIMES!!> 占位符
                response.content = response.content.replace(
                    b'<!!LOAD_TIMES!!>', str.encode(str(cast_time)[:5]))
                    
            except Exception as e:
                # 记录处理过程中的任何错误
                logger.error("Error OnlineMiddleware: %s" % e)

        # 返回处理后的响应
        return response
